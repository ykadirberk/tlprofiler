# tlprofiler
Thread Local profiler with output to file for C++. Example code is in tlprofiler.cpp.

## Setup

Simply create a cpp file and write this at the top of the file. Then you can start including profiler.h where it should be used.
```
#define TLPROFILER_IMPLEMENTATION
#include "profiler/profiler.h"
```
Output format must be explicitly defined by defining these macros:
```
// Macros below are either defined with every inclusion or defined as a compiler option.
// ----------------
// TLPROFILER_FILE_BUFFERED macro allows the output of profiler to be buffered until thread exit and written to a file. 
// Detached threads might not output anything if the main thread exits first.
// ----------------
// TLPROFILER_FILE_DIRECT macro allows the output of profiler to be written to a file at the function exit.
// Detached threads might not output some of function's output if the main thread exits first.
// ----------------
// TLPROFILER_UDP_DIRECT (only on Windows) macro allows the output of profiler to be sent over udp connection (localhost:5152) in real time.
// PROFILER_UDP_INIT should be run for a single time before any profiling occurs
// PROFILER_UDP_DESTROY should be run after all profiling occurs.
// payload of the udp packet's layout:
// typedef struct _profiler_payload_t
// {
//		uint64_t thread_id;
//		uint64_t start_time_microsec;
//		uint64_t end_time_microsec;
//		uint64_t elapsed_time_microsec;
//		uint64_t call_stack_size;
//		char call_stack[1024];
// }
// profiler_payload_t;
// ----------------
```

After that, using PROFILE macro will allow any scope to be profiled starting from the line it is written. (yet no information about scope will be emitted, only the function name.)

```
void Hello_World()
{
	PROFILE
	std::cout << "Hello World." << std::endl;
}
```
using PROFILE_NAME("custom_name") will help naming scopes with custom names.
```
void Hello_World()
{
	PROFILE
	PROFILE_NAME("custom")
	std::cout << "Hello World." << std::endl;
}

```


As a note, using TLPROFILER_UDP_DIRECT requires some other macros to be executed. An example code:

```
#define TLPROFILER_IMPLEMENTATION
#define TLPROFILER_UDP_DIRECT
#include "profiler/profiler.h"

int main() 
{
	PROFILER_UDP_INIT
	{
		PROFILE
		std::cout << "Hello World." << std::endl;
	}
	PROFILER_UDP_DESTROY
	return EXIT_SUCCESS;
}

```

## Output for tlprofiler.cpp

### profiler-17620.txt
```
 -> [14]main -> [23]Hello_World -> [34]Message ::: 1775004546113097 - 1775004546114823 ::: 1726 microseconds 
 -> [14]main -> [23]Hello_World -> [34]Message ::: 1775004546115750 - 1775004546116300 ::: 550 microseconds 
 -> [14]main -> [23]Hello_World -> [34]Message ::: 1775004546116314 - 1775004546117797 ::: 1483 microseconds 
 -> [14]main -> [23]Hello_World -> [34]Message ::: 1775004546117817 - 1775004546119103 ::: 1286 microseconds 
 -> [14]main -> [23]Hello_World -> [34]Message ::: 1775004546119122 - 1775004546120114 ::: 991 microseconds 
 -> [14]main -> [23]Hello_World ::: 1775004546112967 - 1775004546120136 ::: 7168 microseconds 
 -> [14]main ::: 1775004546112964 - 1775004546120652 ::: 7688 microseconds 
```

### profiler-38460.txt
```
 -> [23]Hello_World -> [34]Message ::: 1775004546114954 - 1775004546115333 ::: 379 microseconds 
 -> [23]Hello_World -> [34]Message ::: 1775004546115754 - 1775004546116674 ::: 919 microseconds 
 -> [23]Hello_World -> [34]Message ::: 1775004546116693 - 1775004546117530 ::: 836 microseconds 
 -> [23]Hello_World -> [34]Message ::: 1775004546117548 - 1775004546119066 ::: 1517 microseconds 
 -> [23]Hello_World -> [34]Message ::: 1775004546119084 - 1775004546119958 ::: 874 microseconds 
 -> [23]Hello_World ::: 1775004546114911 - 1775004546119973 ::: 5062 microseconds 
```

### Injector script
This script injects the macro to all C++ functions within the given folder and includes the provided header file. Header is just a string so it should be the path your compiler will allow. Usage is:
```
inject_macro.py --folder FOLDER --macro MACRO --header HEADER [--dry-run] [--no-recurse]
```
Example shell prompt
```
py .\inject_macro.py --folder ./tlprofiler/ --macro PROFILE --header profiler/profiler.h
```
### Visualizer (for TLPROFILER_UDP_DIRECT)
Simply run below code on shell, go to http://localhost:3000/ and then run your profiler injected code. 
```
cd visualizer
npm start
```