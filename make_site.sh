cd docs
make html
cp -r build/html/* ../public/
rm -rf build
cd ..
