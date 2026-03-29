// TLPROFILER_IMPLEMENTATION and SWRAP_IMPLEMENTATION should be defined in a cpp file before using anywhere else.
// 
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
#pragma once


#include <string>
#include <chrono>

#if defined(TLPROFILER_UDP_DIRECT)
#include "ext/swrap.h"

typedef struct _profiler_payload_t
{
	uint64_t thread_id;
	uint64_t start_time_microsec;
	uint64_t end_time_microsec;
	uint64_t elapsed_time_microsec;
	uint64_t call_stack_size;
	char call_stack[1024];
} 
profiler_payload_t;
#endif

#if defined(TLPROFILER_FILE_DIRECT) || defined(TLPROFILER_FILE_BUFFERED)
#include <fstream>
#include <filesystem>
#endif

class __my_profiler_class
{
	public:
		__my_profiler_class(const std::string location);
		~__my_profiler_class();

#if defined(TLPROFILER_UDP_DIRECT)
		static void profiler_udp_init();
		static void profiler_udp_destroy();
#endif
	private:
		static inline thread_local std::string call_stack = "";

#if defined(TLPROFILER_FILE_BUFFERED)
		static inline thread_local int buffer_counter = 0;
		static inline thread_local std::stringstream buffer;
#endif

#if defined(TLPROFILER_FILE_DIRECT)
		static inline thread_local std::ofstream outfile;
#endif

#if defined(TLPROFILER_UDP_DIRECT)
		static inline int sock;
#endif

		std::chrono::time_point<std::chrono::system_clock> start_time;

		static std::string_view get_cached_id();
		uint64_t get_cached_id_int();

		static std::string_view remove_last_call(std::string_view t);
};

#define _MYPROFILE_1(x, y)	x##y
#define _MYPROFILE_2(x, y)	_MYPROFILE_1(x, y)
#define _MYPROFILE_3(x)		_MYPROFILE_2(x, __COUNTER__)
#define PROFILE				__my_profiler_class _MYPROFILE_3(var_profiler)(__func__);

#ifdef TLPROFILER_IMPLEMENTATION

__my_profiler_class::__my_profiler_class(const std::string location)
{

#if defined(TLPROFILER_FILE_BUFFERED)
	if (0 == buffer_counter)
	{
		buffer.str("");
	}
	buffer_counter++;
#endif // defined(TLPROFILER_FILE_BUFFERED)

#if defined(TLPROFILER_FILE_DIRECT)
	if (false == outfile.is_open())
	{
		std::filesystem::create_directory("profiling");
		outfile.open(std::string("./profiling/profiler-") + std::string(get_cached_id()) + ".txt", std::ios::ate);
	}
#endif // defined(TLPROFILER_FILE_DIRECT)

	call_stack += " -> ";
	call_stack += location;

	start_time = std::chrono::system_clock::now();
}

__my_profiler_class::~__my_profiler_class()
{
	auto end_time = std::chrono::system_clock::now();

#if defined(TLPROFILER_FILE_BUFFERED)
	buffer_counter--;
	buffer << call_stack << " ::: "
		<< std::chrono::duration_cast<std::chrono::microseconds>(start_time.time_since_epoch()).count() << " - "
		<< std::chrono::duration_cast<std::chrono::microseconds>(end_time.time_since_epoch()).count() << " ::: "
		<< std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time).count() << " microseconds \n";
	
	if (0 == buffer_counter)
	{
		std::filesystem::create_directory("profiling");
		std::ofstream outfile(std::string("./profiling/profiler-") + std::string(get_cached_id()) + ".txt", std::ios::ate);
		if (outfile.is_open())
		{
			outfile << buffer.str();
			outfile.close();
		}
	}
#endif

#if defined(TLPROFILER_FILE_DIRECT)
	outfile << call_stack << " ::: "
		<< std::chrono::duration_cast<std::chrono::microseconds>(start_time.time_since_epoch()).count() << " - "
		<< std::chrono::duration_cast<std::chrono::microseconds>(end_time.time_since_epoch()).count() << " ::: "
		<< std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time).count() << " microseconds \n";
	outfile.flush();
#endif

#if defined(TLPROFILER_UDP_DIRECT)
	
	profiler_payload_t payload;
	payload.thread_id             = get_cached_id_int();
	payload.start_time_microsec   = get_cached_id_int();
	payload.end_time_microsec     = get_cached_id_int();
	payload.elapsed_time_microsec = get_cached_id_int();
	payload.call_stack_size       = get_cached_id_int();
	memcpy(payload.call_stack, call_stack.data(), call_stack.size() < 1024 ? call_stack.size() : 1024 );
	swrapSend(sock, static_cast<const char*>(static_cast<void*>(&payload)), sizeof(payload));

#endif

	call_stack = remove_last_call(call_stack);
}

std::string_view __my_profiler_class::get_cached_id()
{
	static thread_local std::string cached_id = []()
	{
		std::stringstream ss;
		ss << std::this_thread::get_id();
		return ss.str();
	}();

	
	return cached_id;
}

uint64_t __my_profiler_class::get_cached_id_int()
{
	static thread_local uint64_t cached_id = []()
	{
		std::stringstream ss;
		ss << std::this_thread::get_id();
		uint64_t t;
		ss >> t;
		return t;
	}();

	return cached_id;
}

std::string_view __my_profiler_class::remove_last_call(std::string_view t)
{
	if (auto i = t.find_last_of("->"); i != std::string::npos)
	{
		return t.substr(0, i - 2);
	}
	return "";
}

#if defined(TLPROFILER_UDP_DIRECT)
#define PROFILER_UDP_INIT		__my_profiler_class::profiler_udp_init();
#define PROFILER_UDP_DESTROY	__my_profiler_class::profiler_udp_destroy();

void __my_profiler_class::profiler_udp_init()
{
	swrapInit();
	sock = swrapSocket(SWRAP_UDP, SWRAP_BIND, SWRAP_NOBLOCK, "127.0.0.1", "5152");
}

void __my_profiler_class::profiler_udp_destroy()
{
	swrapClose(sock);
	swrapTerminate();
}

#endif

#endif // TLPROFILER_IMPLEMENTATION
