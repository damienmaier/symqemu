The binary here has been optained the following way :

- Clone https://github.com/uclouvain/openjpeg and checkout commit 6af3931
- Edit `CMakelists.txt` and add `set(CMAKE_EXE_LINKER_FLAGS "-static")` at the top

```
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make
```

The binary is `bin/opj_decompress`
