# Must run script from repo base dir, otherwise will exit
outdir=docs/notebook_build/
cd docs/ || exit 1;
mkdir -p notebook_build
# Clean up notebook_build direcotry
rm notebook_build/*
cd ../examples || exit 1;

fail=0
failed_files=()
# Only do this for files ending in _notebook.py
for f in *_notebook.py
do
    # Strip filename of ext
    outfn=(${f//./ });
    echo "$f to $outfn.html";
    # Use Jupytext to convert python to notebook 
    # Pipe through stdin to jupyter
    # Use jupyter nbconvert to execute and convert to html
    # jupytext outputs final html file to stdout, but we don't need it
    # since jupyter has already made the file, so send to /dev/null
    jupytext --to ipynb --pipe-fmt ipynb -o '-' --check \
        "jupyter nbconvert --to html --execute --stdin --output ../$outdir/$outfn.html" $f > /dev/null;
    
    # Check output of jupytext, if it fails, keep running but store the fail flag for later
    if [[ $? -ne 0 ]]; then
      fail=1;
      failed_files+=("$f")
    fi
done

if [[ $fail == 1 ]]; then
    echo "Files ${failed_files[@]} failed";
    exit 1
fi
