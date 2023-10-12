# Type-safe Python contract interfaces for the Hyperdrive ecosystem

Generate the requisite Python files by running:

```bash
sh pypechain path/to/ABIs --output_dir path/to/temp_dir
```

and then moving the generated files to lib/hypertypes/hypertypes

You can then pip install the package from the project root with

```bash
pip install -e lib/hypertypes[base]
```
