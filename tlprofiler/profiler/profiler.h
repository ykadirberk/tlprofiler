#pragma once
#include <string>
#include <fstream>
#include <thread>
#include <chrono>
#include <source_location>

class __my_profiler_class
{
	public:
		__my_profiler_class(const std::source_location location = std::source_location::current())
		{
			call_stack += " -> ";
			call_stack += location.function_name();
			if (false == outfile.is_open())
			{
				outfile.open(std::string("./profiler-") + get_cached_id() + ".txt", std::ios::ate);
			}
			start_time = std::chrono::system_clock::now();
		}

		~__my_profiler_class()
		{
			auto end_time = std::chrono::system_clock::now();
			outfile << call_stack << " ::: " 
					<< std::chrono::duration_cast<std::chrono::microseconds>(start_time.time_since_epoch()).count() << " - " 
					<< std::chrono::duration_cast<std::chrono::microseconds>(end_time  .time_since_epoch()).count() << " ::: " 
					<< std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time).count() << " microseconds \n";
			call_stack = remove_last_call(call_stack);
		}
	private:
		static inline thread_local std::string call_stack = "";
		static inline thread_local std::ofstream outfile;

		std::chrono::time_point<std::chrono::system_clock> start_time;

		static std::string get_cached_id()
		{
			static thread_local std::string cached_id = []()
			{
				std::stringstream ss;
				ss << std::this_thread::get_id();
				return ss.str();
			}();

			return cached_id;
		}

		static std::string remove_last_call(std::string_view t)
		{
			if (auto i = t.find_last_of("->"); i != std::string::npos)
			{
				return std::string(t.substr(0, i - 2));
			}
			return "";
		}
};

#define _MYPROFILE_1(x, y)	x##y
#define _MYPROFILE_2(x, y)	_MYPROFILE_1(x, y)
#define _MYPROFILE_3(x)		_MYPROFILE_2(x, __COUNTER__)
#define PROFILE				__my_profiler_class _MYPROFILE_3(var_profiler);