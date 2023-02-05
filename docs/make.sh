rm -rf build ../html source/autoapi
make html
cp -r build/html/ ..
rm -rf build
