#include <iostream>
#include <thread>

#define TLPROFILER_IMPLEMENTATION
#define TLPROFILER_FILE_BUFFERED
#define SWRAP_IMPLEMENTATION

#include "profiler/profiler.h"

void Hello_World();
void Message();

int main()
{
	auto t = std::thread(&Hello_World);
	PROFILE
	Hello_World();
	std::cout << "Hello CMake." << std::endl;
	t.join();
	return EXIT_SUCCESS;
}

void Hello_World()
{
	PROFILE
	std::cout << "Hello World." << std::endl;
	Message();
	Message();
	Message();
	Message();
	Message();
}

void Message()
{
	PROFILE
	std::cout << "message1." << std::endl;
	std::cout << "message2." << std::endl;
	std::cout << "message3." << std::endl;
	std::cout << "message4." << std::endl;
	std::cout << "message5." << std::endl;
	std::cout << "message6." << std::endl;
	std::cout << "message7." << std::endl;
	std::cout << "message8." << std::endl;
	std::cout << "message9." << std::endl;
	std::cout << "message0." << std::endl;
}
