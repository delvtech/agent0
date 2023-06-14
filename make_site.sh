if [ ! -d "$DIRECTORY" ]; then
  mkdir public  # make ./public if it doesn't exist
fi

# use sphinx to build docs
cd docs
make html

# move built html files to ./public
cp -r build/html/* ../public/
echo "moved html pages from ./docs/build/html to ./public"

# delete build folder
rm -rf build

# return to elf-simulations root
cd ..
