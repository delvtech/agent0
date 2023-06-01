rm -rf public docs/source/autoapi
mkdir public
cd docs
make notebook
make html
cp -r build/html/* ../public/
rm -rf build
