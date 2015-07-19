#!/bin/bash

[ "$#" -eq 0 ] && echo "usage: $0 config_file" && exit

# load config file
[ ! -e "$1" ] && echo "no such file: $1" && exit
. "$1"

# set default values
: ${NAME:=`basename "$1" .cfg`}
: ${TARGET_DIR:="build/$NAME"}
[ -z "$BLAS_NAME" ] && echo "BLAS_NAME is not set" && exit
: ${SYSTEM_NAME:="local"}
: ${NCORES:=1}
: ${THREADS_PER_CORE:=1}
: ${CC:=gcc}
[ "$CC" == "gcc" ] && : ${CFLAGS:="-fopenmp"} || : {$CFLAGS:=""}
: ${CXX:=g++}
[ "$CXX" == "g++" ] && : ${CXXFLAGS:="-fopenmp"} || : ${CXXFLAGS:=""}
: ${LINK_FLAGS:=""}
: ${INCLUDE_FLAGS:=""}
: ${KERNEL_HEADERS:=`echo ../resources/headers/{blas_,lapack_,utility}.h`}
: ${OPENMP:=1}
: ${PAPI_COUNTERS_MAX:=0}
: ${PAPI_COUNTERS_AVAIL:=""}
: ${BACKEND:="local"}
: ${BACKEND_HEADER:=""}
: ${BACKEND_PREFIX:=""}
: ${BACKEND_SUFFIX:=""}
: ${BACKEND_FOOTER:=""}
[ -n "$DFLOPS_PER_CYCLE" -a -z "$SFLOPS_PER_CYCLE" ] && SFLOPS_PER_CYCLE=$((DFLOPS_PER_CYCLE * 2))
[ -n "$SFLOPS_PER_CYCLE" -a -z "$DFLOPS_PER_CYCLE" ] && DFLOPS_PER_CYCLE=$((SFLOPS_PER_CYCLE / 2))

export TARGET_DIR NAME BLAS_NAME SYSTEM_NAME KERNEL_HEADERS
export BACKEND BACKEND_HEADER BACKEND_PREFIX BACKEND_SUFFIX BACKEND_FOOTER
export PAPI_COUNTERS_MAX PAPI_COUNTERS_AVAIL OPENMP
export DFLOPS_PER_CYCLE SFLOPS_PER_CYCLE 
export CPU_MODEL FREQUENCY_HZ NCORES THREADS_PER_CORE

# print info
echo "Building Sampler  $NAME"
echo "build folder:     $TARGET_DIR"
echo "system/BLAS:      $SYSTEM_NAME/$BLAS_NAME"
echo "CPU (Hz):         $CPU_MODEL ($FREQUENCY_HZ)"
echo "#cores:           $NCORES"
echo "threads/core:     $THREADS_PER_CORE"
echo "flops/cycle:      $SFLOPS_PER_CYCLE (single) / $DFLOPS_PER_CYCLE (double)"
echo "kernels:          $KERNEL_HEADERS"
echo -n "OpenMP:           "
[ $OPENMP -eq 1 ] && echo "Enabled" || echo "Disabled"
echo "C compiler:       $CC $CFLAGS"
echo "C++ compiler:     $CXX $CXXFLAGS"
echo "include flags:    $INCLUDE_FLAGS"
echo "linker flags:     $LINK_FLAGS"
if [ $PAPI_COUNTERS_MAX -eq 0 ]; then
    echo "PAPI:             Disabled"
else
    echo "#PAPI counters:   $PAPI_COUNTERS_MAX"
    echo "PAPI counters:    $PAPI_COUNTERS_AVAIL"
fi
echo "backend:          $BACKEND"
[ -z "$BACKEND_HEADER" ] || echo "backend header:   $BACKEND_HEADER"
[ -z "$BACKEND_PREFIX" ] || echo "backend prefix:   $BACKEND_PREFIX"
[ -z "$BACKEND_SUFFIX" ] || echo "backend suffix:   $BACKEND_SUFFIX"
[ -z "$BACKEND_FOOTER" ] || echo "backend footer:   $BACKEND_FOOTER"
echo -n "compiling "

# set paths
cfg_h=$TARGET_DIR/cfg.h
kernel_h=$TARGET_DIR/kernels.h
sigs_c_inc=$TARGET_DIR/sigs.c.inc
calls_c_inc=$TARGET_DIR/calls.c.inc
info_py=$TARGET_DIR/info.py

# clean previous build
rm -rf "$TARGET_DIR"

# craete buld directory
mkdir -p "$TARGET_DIR"

# create headers file
src/create_header.py > "$kernel_h"
echo -n "."

# create aux files
$CC $CFLAGS -E -I. "$kernel_h" | src/create_incs.py "$cfg_h" "$kernel_h" "$sigs_c_inc" "$calls_c_inc" "$info_py" || exit
echo -n "."

defines=""
[ "$OPENMP" == "1" ] && defines+=" -D OPENMP_ENABLED"
[ "$PAPI_COUNTERS_MAX" -gt 0 ] && defines+=" -D PAPI_ENABLED"
# build .o
for x in main CallParser MemoryManager Sampler Signature; do
    $CXX $CXXFLAGS $INCLUDE_FLAGS -I. -c -D CFG_H="\"$cfg_h\"" $defines $defineother src/$x.cpp -o "$TARGET_DIR/$x.o" || exit
    echo -n "."
done

# build kernels
mkdir "$TARGET_DIR/kernels"
for file in kernels/*.c; do
    $CC $CFLAGS -c $file -o "$TARGET_DIR/${file%.c}.o" || exit
    echo -n "."
done

# build sample.o
$CC $CFLAGS $INCLUDE_FLAGS -I. -c -D CFG_H="\"$cfg_h\"" $defines src/sample.c -o "$TARGET_DIR/sample.o" || exit
echo -n "."

# build sampler
$CXX $CXXFLAGS "$TARGET_DIR/"*.o "$TARGET_DIR/kernels/"*.o -o "$TARGET_DIR/sampler.x" $LINK_FLAGS || exit
echo " Done!"
