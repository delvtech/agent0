rm -rf public docs/source/autoapi
mkdir public
cd docs
make html
cp -r build/html/ ../public/
