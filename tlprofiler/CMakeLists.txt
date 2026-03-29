# CMakeList.txt : CMake project for tlrprofiler, include source and define
# project specific logic here.
#

# Add source to this project's executable.
add_executable (tlprofiler "tlprofiler.cpp" "profiler/profiler.h" )

if (CMAKE_VERSION VERSION_GREATER 3.12)
  set_property(TARGET tlprofiler PROPERTY CXX_STANDARD 20)
endif()


target_link_libraries("tlprofiler" ws2_32)

# TODO: Add tests and install targets if needed.
