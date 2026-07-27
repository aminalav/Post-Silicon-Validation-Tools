cmake_minimum_required(VERSION 3.15)
project(sep_core_native_tests LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(test_sep_core
  test_core.cpp
  ../src/log_parser.cpp
  ../src/reg_decoder.cpp
)
target_include_directories(test_sep_core PRIVATE ../include)
target_compile_options(test_sep_core PRIVATE
  $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall -Wextra>
)

enable_testing()
add_test(NAME sep_core_native COMMAND test_sep_core)
