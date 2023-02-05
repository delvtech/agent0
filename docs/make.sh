rm -rf build public source/autoapi
make html
cp -r build/html public
rm -rf build
