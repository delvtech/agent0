rm -rf build html docs/source/autoapi
cd docs
make html
cp -r build/html/ html