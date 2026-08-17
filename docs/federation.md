# Federation

In this section, we will explain how to use the federation setup. For a component to use federation needs to have implemented the next methods.

```python
    def to_binary(self) -> bytes | None:
    """(Federation only) fill it to be compatible with federation ops"""

    def from_binary(self, binary: bytes) -> object:
    """(Federation only) fill it to be compatible with federation ops"""

    def aggregate_strategy(self, components: set["FedOperations"]) -> None:
    """(Federation only) fill it to be compatible with federation ops"""
```

There are two man ways to use federation:

* **Combine first**: only can be use when all components run locally. The main idea is to simplify the process by allowing components to share memory.
* **Stack later**: a more standard approach to federated where the "weights" of each component are combine at the end.

## Example class

For all the examplaes bellow, we will use this code:

```python
--8<-- "docs/examples/others/federation.py:example_1"
```


## Combine first

The diagram bellow show the workflow:

![combine](img/fed_combine_first.png)


Example 1:

```python
--8<-- "docs/examples/others/federation.py:example_2"
```

Example 2:

```python
--8<-- "docs/examples/others/federation.py:example_3"
```

## Stack

The diagram bellow show the workflow:

![combine](img/fed_stack_later.png)

Example 1:

```python
--8<-- "docs/examples/others/federation.py:example_4"
```

Example 2:

```python
--8<-- "docs/examples/others/federation.py:example_5"
```
