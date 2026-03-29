# tlprofiler
Thread Local profiler with output to file for C++. Example code is in tlprofiler.cpp.

## Setup

Simply create a cpp file and write this at the top of the file. Then you can start including profiler.h where it should be used.
```
#define TLPROFILER_IMPLEMENTATION
#define SWRAP_IMPLEMENTATION
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
// TLPROFILER_UDP_DIRECT macro allows the output of profiler to be sent over udp connection (localhost:5152) in real time.
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

As a note, using TLPROFILER_UDP_DIRECT requires some other macros to be executed. An example code:

```
#define TLPROFILER_IMPLEMENTATION
#define TLPROFILER_UDP_DIRECT
#define SWRAP_IMPLEMENTATION
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
 -> main -> Hello_World -> Message ::: 1774749448813808 - 1774749448816386 ::: 2578 microseconds 
 -> main -> Hello_World -> Message ::: 1774749448816491 - 1774749448818160 ::: 1668 microseconds 
 -> main -> Hello_World -> Message ::: 1774749448818209 - 1774749448819996 ::: 1787 microseconds 
 -> main -> Hello_World -> Message ::: 1774749448820015 - 1774749448820519 ::: 503 microseconds 
 -> main -> Hello_World -> Message ::: 1774749448820536 - 1774749448820989 ::: 453 microseconds 
 -> main -> Hello_World ::: 1774749448813706 - 1774749448821003 ::: 7297 microseconds 
 -> main ::: 1774749448813704 - 1774749448821046 ::: 7341 microseconds 
```

### profiler-38460.txt
```
 -> Hello_World -> Message ::: 1774749448816457 - 1774749448816989 ::: 532 microseconds 
 -> Hello_World -> Message ::: 1774749448817009 - 1774749448817457 ::: 448 microseconds 
 -> Hello_World -> Message ::: 1774749448817476 - 1774749448817839 ::: 362 microseconds 
 -> Hello_World -> Message ::: 1774749448817844 - 1774749448818541 ::: 697 microseconds 
 -> Hello_World -> Message ::: 1774749448818557 - 1774749448819303 ::: 745 microseconds 
 -> Hello_World ::: 1774749448816322 - 1774749448819318 ::: 2996 microseconds 
```

### The injector script
Usage is
```
inject_macro.py --folder FOLDER --macro MACRO --header HEADER [--dry-run] [--no-recurse]
```

This script injects the macro to all C++ functions within the given folder and includes the provided header file. Header is just a string so it should be the path your compiler will allow.

```
py .\inject_macro.py --folder ./tlprofiler/ --macro PROFILE --header profiler/profiler.h
```

