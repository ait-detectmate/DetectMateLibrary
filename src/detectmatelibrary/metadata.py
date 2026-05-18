__authors__ = [{"name": "André García Gómez"}, {"name": "Viktor Beck"}, {"name": "Thorina Boenke"},
               {"name": "Markus Wurzenberger"}, {"name": "Max Landauer"}, {"name": "Wolfgang Hotwagner"},
               {"name": "Anna Erdi"}, {"name": "Ernst Leierzopf"}, {"name": "Florian Skopik"}]
__contact__ = "aecid@ait.ac.at"
__copyright__ = "Copyright 2026, AIT Austrian Institute of Technology GmbH"
__date__ = "2026/05/18"
__deprecated__ = False
__email__ = "aecid@ait.ac.at"
__website__ = "https://aecid.ait.ac.at"
__license__ = "EUPL-1.2"
__maintainers__ = [{"name": "Markus Wurzenberger", "email": "aecid@ait.ac.at"}]
__status__ = "Development"
__version__ = "0.2.0"
_indentation = max(0, (29 - len(__version__)) // 2)
__version_string__ = """   (Austrian Institute of Technology)\n       (%s)\n%sVersion: %s""" % (
    __website__, " " * _indentation, __version__ + " " * _indentation)
__all__ = ['__authors__', '__contact__', '__copyright__', '__date__', '__deprecated__', '__email__', '__website__', '__license__',
           '__maintainers__', '__status__', '__version__', '__version_string__']
del _indentation