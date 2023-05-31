Elfpy documentation and notebook examples can be built locally using the provided Makefile. To build local documentations that include notebook examples in `examples/*_notebooks.py`, run from this directory

```
make notebook;
make html
```
This executes and converts all the `jupytext` notebooks in `examples/*_notebooks.py` to html files and creates the documentation with links to the notebooks using Sphinx. Note that documentation built in CI does not include notebook examples.
