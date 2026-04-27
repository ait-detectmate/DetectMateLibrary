"""Integration tests for Service with multi-destination output."""
import socket
import pytest
import time
import pynng
import httpx
import threading

from service.core import Service
from service.settings import ServiceSettings


class MockService(Service):
    """Concrete test service."""
    component_type = "test_service"


@pytest.fixture
def free_port():
    """Find a free port on the system."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


@pytest.fixture
def temp_ipc_paths(tmp_path):
    """Generate temporary IPC paths for testing."""
    return {
        'engine': f"ipc://{tmp_path}/engine.ipc",
        'out1': f"ipc://{tmp_path}/out1.ipc",
        'out2': f"ipc://{tmp_path}/out2.ipc",
        'out3': f"ipc://{tmp_path}/out3.ipc",
    }


def run_service_in_thread(service):
    """Helper to start the service.run() in a background thread."""
    thread = threading.Thread(target=service.run, daemon=True)
    thread.start()
    # Wait for web server to likely be up
    time.sleep(0.5)
    return thread


class TestServiceMultiOutputIntegration:
    """Integration tests for Service with multi-output functionality."""

    def test_service_with_multiple_outputs(self, temp_ipc_paths, tmp_path, free_port):
        port = free_port
        """Test complete service flow with multiple outputs."""
        settings = ServiceSettings(
            component_name="test-service",
            engine_addr=temp_ipc_paths['engine'],
            http_host="127.0.0.1",
            http_port=port,
            out_addr=[temp_ipc_paths['out1'], temp_ipc_paths['out2']],
            log_dir=tmp_path / "logs",
            engine_autostart=True,
        )

        # Create output receivers
        receivers = []
        for addr in [temp_ipc_paths['out1'], temp_ipc_paths['out2']]:
            receiver = pynng.Pair0()
            receiver.listen(addr)
            receiver.recv_timeout = 1000
            receivers.append(receiver)

        # Create service
        service = MockService(settings=settings)
        run_service_in_thread(service)

        # Create input sender
        sender = pynng.Pair0()
        sender.dial(temp_ipc_paths['engine'])

        try:
            time.sleep(0.2)  # Give service time to start

            # Send test message
            test_message = b"integration test"
            sender.send(test_message)

            # All receivers should get the message
            for receiver in receivers:
                result = receiver.recv()
                assert result == test_message  # Default processor echoes

        finally:
            service.stop()
            sender.close()
            for receiver in receivers:
                receiver.close()
            try:
                httpx.post(f"http://127.0.0.1:{port}/admin/shutdown")
            except Exception:
                pass  # Server might already be down

    def test_service_status_with_output_config(self, temp_ipc_paths, tmp_path, free_port):
        port = free_port
        """Test that status command includes output configuration."""

        settings = ServiceSettings(
            component_name="status-test",
            engine_addr=temp_ipc_paths['engine'],
            http_host="127.0.0.1",
            http_port=port,
            out_addr=[temp_ipc_paths['out1'], temp_ipc_paths['out2']],
            log_dir=tmp_path / "logs",
            engine_autostart=True,
        )

        # output listeners must exist before service starts
        r1 = pynng.Pair0()
        r1.listen(temp_ipc_paths['out1'])
        r2 = pynng.Pair0()
        r2.listen(temp_ipc_paths['out2'])
        r1.recv_timeout = r2.recv_timeout = 1000

        service = MockService(settings=settings)
        run_service_in_thread(service)

        try:
            time.sleep(0.5)

            # Request status via HTTP instead of NNG Manager
            response = httpx.get(f"http://127.0.0.1:{port}/admin/status")
            assert response.status_code == 200
            status_data = response.json()

            # Verify output addresses are in settings
            assert 'settings' in status_data
            assert status_data['settings']['out_addr'] == [
                temp_ipc_paths['out1'],
                temp_ipc_paths['out2']
            ]

        finally:
            service.stop()
            r1.close()
            r2.close()
            try:
                httpx.post(f"http://127.0.0.1:{port}/admin/shutdown")
            except Exception:
                pass  # Server might already be down

    def test_service_context_manager_with_outputs(self, temp_ipc_paths, tmp_path, free_port):
        port = free_port
        """Test service as context manager with multiple outputs."""
        settings = ServiceSettings(
            component_name="context-test",
            engine_addr=temp_ipc_paths['engine'],
            http_host="127.0.0.1",
            http_port=port,
            out_addr=[temp_ipc_paths['out1']],
            log_dir=tmp_path / "logs",
            engine_autostart=True,
        )

        receiver = pynng.Pair0()
        receiver.listen(temp_ipc_paths['out1'])
        receiver.recv_timeout = 1000

        sender = pynng.Pair0()
        sender.dial(temp_ipc_paths['engine'])

        service = MockService(settings=settings)
        run_service_in_thread(service)
        try:
            time.sleep(0.1)
            # Send message
            sender.send(b"context manager test")
            # Receive message
            result = receiver.recv()
            assert result == b"context manager test"

        finally:
            sender.close()
            receiver.close()
            try:
                httpx.post(f"http://127.0.0.1:{port}/admin/shutdown")
            except Exception:
                pass  # Server might already be down

    def test_service_stop_command_closes_outputs(self, temp_ipc_paths, tmp_path, free_port):
        port = free_port
        """Test that stop command properly closes output sockets."""
        settings = ServiceSettings(
            component_name="stop-test",
            engine_addr=temp_ipc_paths['engine'],
            http_host="127.0.0.1",
            http_port=port,
            out_addr=[temp_ipc_paths['out1'], temp_ipc_paths['out2']],
            log_dir=tmp_path / "logs",
            engine_autostart=True,
        )

        # listeners required before starting service
        r1 = pynng.Pair0()
        r1.listen(temp_ipc_paths['out1'])
        r2 = pynng.Pair0()
        r2.listen(temp_ipc_paths['out2'])
        r1.recv_timeout = r2.recv_timeout = 1000

        service = MockService(settings=settings)
        run_service_in_thread(service)

        try:
            # Verify service is running
            assert service._running

            # Send stop command
            httpx.post(f"http://127.0.0.1:{port}/admin/stop")

            time.sleep(0.2)  # Give time to stop

            # Verify service stopped
            assert not service._running

            # Verify output sockets are closed
            for sock in service._out_sockets:
                with pytest.raises(pynng.NNGException):
                    sock.send(b"test")

        finally:
            r1.close()
            r2.close()
            try:
                httpx.post(f"http://127.0.0.1:{port}/admin/shutdown")
            except Exception:
                pass  # Server might already be down

    def test_service_with_no_outputs_still_works(self, temp_ipc_paths, tmp_path, free_port):
        port = free_port
        """Test that service works normally with no output addresses."""
        settings = ServiceSettings(
            component_name="no-output-test",
            engine_addr=temp_ipc_paths['engine'],
            http_host="127.0.0.1",
            http_port=port,
            out_addr=[],  # Empty list
            log_dir=tmp_path / "logs",
            engine_autostart=True,
        )

        service = MockService(settings=settings)
        run_service_in_thread(service)

        sender = pynng.Pair0()
        sender.dial(temp_ipc_paths['engine'])

        try:
            time.sleep(0.1)

            # Service should handle messages even without outputs
            sender.send(b"test message")
            time.sleep(0.1)

            # Service should still be running
            assert service._running

        finally:
            service.stop()
            sender.close()
            try:
                httpx.post(f"http://127.0.0.1:{port}/admin/shutdown")
            except Exception:
                pass  # Server might already be down

    def test_yaml_config_loading_with_outputs(self, tmp_path, free_port):
        port = free_port
        """Test loading service settings from YAML with output addresses."""
        yaml_content = """
        component_name: "yaml-test"
        component_type: "test_service"
        log_dir: "{log_dir}"
        http_host: "127.0.0.1"
        http_port: {port}
        engine_addr: "ipc://{tmp}/engine.ipc"
        out_addr:
          - "ipc://{tmp}/out1.ipc"
          - "ipc://{tmp}/out2.ipc"
          - "tcp://localhost:5555"
        engine_autostart: false
        """.format(log_dir=str(tmp_path / "logs"), tmp=str(tmp_path), port=port)

        yaml_file = tmp_path / "settings.yaml"
        yaml_file.write_text(yaml_content)

        settings = ServiceSettings.from_yaml(yaml_file)

        assert settings.component_name == "yaml-test"
        assert len(settings.out_addr) == 3

        out_strs = [str(a) for a in settings.out_addr]
        assert f"ipc://{tmp_path}/out1.ipc" in out_strs
        assert f"ipc://{tmp_path}/out2.ipc" in out_strs
        assert "tcp://localhost:5555" in out_strs

        assert [a.scheme for a in settings.out_addr] == ["ipc", "ipc", "tcp"]

    def test_concurrent_services_different_outputs(self, tmp_path, free_port):
        port = free_port
        """Test multiple services with different output destinations."""
        # Service 1 setup
        service1_paths = {
            'engine': f"ipc://{tmp_path}/service1_engine.ipc",
            'out': f"ipc://{tmp_path}/service1_out.ipc",
        }
        settings1 = ServiceSettings(
            component_name="service-1",
            engine_addr=service1_paths['engine'],
            http_host="127.0.0.1",
            http_port=port,
            out_addr=[service1_paths['out']],
            log_dir=tmp_path / "logs1",
            engine_autostart=True,
        )

        # Service 2 setup
        service2_paths = {
            'engine': f"ipc://{tmp_path}/service2_engine.ipc",
            'out': f"ipc://{tmp_path}/service2_out.ipc",
        }
        settings2 = ServiceSettings(
            component_name="service-2",
            engine_addr=service2_paths['engine'],
            http_host="127.0.0.1",
            http_port=port+1,
            out_addr=[service2_paths['out']],
            log_dir=tmp_path / "logs2",
            engine_autostart=True,
        )

        # Create receivers
        receiver1 = pynng.Pair0()
        receiver1.listen(service1_paths['out'])
        receiver1.recv_timeout = 1000

        receiver2 = pynng.Pair0()
        receiver2.listen(service2_paths['out'])
        receiver2.recv_timeout = 1000

        # Create services
        service1 = MockService(settings=settings1)
        run_service_in_thread(service1)
        service2 = MockService(settings=settings2)
        run_service_in_thread(service2)

        # Create senders
        sender1 = pynng.Pair0()
        sender1.dial(service1_paths['engine'])

        sender2 = pynng.Pair0()
        sender2.dial(service2_paths['engine'])

        try:
            time.sleep(0.2)

            # Send different messages to each service
            sender1.send(b"message for service 1")
            sender2.send(b"message for service 2")

            # Verify each receiver gets correct message
            result1 = receiver1.recv()
            result2 = receiver2.recv()

            assert result1 == b"message for service 1"
            assert result2 == b"message for service 2"

        finally:
            service1.stop()
            service2.stop()
            sender1.close()
            sender2.close()
            receiver1.close()
            receiver2.close()
            try:
                httpx.post(f"http://127.0.0.1:{port}/admin/shutdown")
                httpx.post(f"http://127.0.0.1:{port+1}/admin/shutdown")
            except Exception:
                pass  # Servers might already be down


class TestServiceMultiOutputStressTests:
    """Stress tests for multi-output functionality."""

    def test_high_throughput_multiple_outputs(self, temp_ipc_paths, tmp_path, free_port):
        port = free_port
        """Test handling high message throughput to multiple outputs."""
        settings = ServiceSettings(
            component_name="stress-test",
            engine_addr=temp_ipc_paths['engine'],
            http_host="127.0.0.1",
            http_port=port,
            out_addr=[
                temp_ipc_paths['out1'],
                temp_ipc_paths['out2'],
                temp_ipc_paths['out3'],
            ],
            log_dir=tmp_path / "logs",
            engine_autostart=True,
        )

        # Create receivers
        receivers = []
        for addr in [temp_ipc_paths['out1'], temp_ipc_paths['out2'],
                     temp_ipc_paths['out3']]:
            receiver = pynng.Pair0()
            receiver.listen(addr)
            receiver.recv_timeout = 5000  # Longer timeout for stress test
            receivers.append(receiver)

        service = MockService(settings=settings)
        run_service_in_thread(service)
        sender = pynng.Pair0()
        sender.dial(temp_ipc_paths['engine'])

        try:
            time.sleep(0.2)

            # Send many messages rapidly
            num_messages = 100
            for i in range(num_messages):
                message = f"stress test message {i}".encode()
                sender.send(message)
                time.sleep(0.001)  # Tiny delay

            # Verify all receivers get all messages
            for receiver in receivers:
                received_count = 0
                for i in range(num_messages):
                    try:
                        receiver.recv()
                        received_count += 1
                    except pynng.Timeout:
                        break

                # Should receive most/all messages
                # assert received_count >= num_messages * 0.95  # Allow 5% loss
                assert received_count == num_messages

        finally:
            service.stop()
            sender.close()
            for receiver in receivers:
                receiver.close()
            try:
                httpx.post(f"http://127.0.0.1:{port}/admin/shutdown")
            except Exception:
                pass  # Server might already be down
