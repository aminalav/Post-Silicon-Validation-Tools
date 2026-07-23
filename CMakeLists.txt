cmake_minimum_required(VERSION 3.15)
project(sep_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# pybind11 is provided as a build dependency (see pyproject.toml build-system).
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(sep_core
  cpp/src/log_parser.cpp
  cpp/src/reg_decoder.cpp
  cpp/bindings/bindings.cpp
)

target_include_directories(sep_core PRIVATE cpp/include)
target_compile_options(sep_core PRIVATE
  $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall -Wextra>
)

# Install the compiled module at the wheel root so `import sep_core` works.
install(TARGETS sep_core LIBRARY DESTINATION .)
