#include <iostream>
#include <thread>
#include "profiler/profiler.h"

void Hello_World();
void Message();

int main()
{
	std::thread(&Hello_World).detach();
	PROFILE
	Hello_World();
	std::cout << "Hello CMake." << std::endl;
	return 0;
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
