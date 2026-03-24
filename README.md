# tlprofiler
Thread Local profiler with output to file for C++


## output for example code

### profiler-15832.txt
```
 -> int __cdecl main(void) -> void __cdecl Hello_World(void) -> void __cdecl Message(void) ::: 1774393334639327 - 1774393334640695 ::: 1367 microseconds 
 -> int __cdecl main(void) -> void __cdecl Hello_World(void) -> void __cdecl Message(void) ::: 1774393334640799 - 1774393334641656 ::: 856 microseconds 
 -> int __cdecl main(void) -> void __cdecl Hello_World(void) -> void __cdecl Message(void) ::: 1774393334641678 - 1774393334642558 ::: 880 microseconds 
 -> int __cdecl main(void) -> void __cdecl Hello_World(void) -> void __cdecl Message(void) ::: 1774393334642578 - 1774393334645176 ::: 2598 microseconds 
 -> int __cdecl main(void) -> void __cdecl Hello_World(void) -> void __cdecl Message(void) ::: 1774393334645195 - 1774393334646762 ::: 1566 microseconds 
 -> int __cdecl main(void) -> void __cdecl Hello_World(void) ::: 1774393334638443 - 1774393334646784 ::: 8341 microseconds 
 -> int __cdecl main(void) ::: 1774393334638440 - 1774393334646878 ::: 8437 microseconds 
```

### profiler-39524.txt
```
 -> void __cdecl Hello_World(void) -> void __cdecl Message(void) ::: 1774393334640759 - 1774393334641885 ::: 1126 microseconds 
 -> void __cdecl Hello_World(void) -> void __cdecl Message(void) ::: 1774393334641910 - 1774393334643261 ::: 1351 microseconds 
 -> void __cdecl Hello_World(void) -> void __cdecl Message(void) ::: 1774393334643279 - 1774393334644150 ::: 870 microseconds 
 -> void __cdecl Hello_World(void) -> void __cdecl Message(void) ::: 1774393334644168 - 1774393334644846 ::: 677 microseconds 
 -> void __cdecl Hello_World(void) -> void __cdecl Message(void) ::: 1774393334644892 - 1774393334645895 ::: 1002 microseconds 
 -> void __cdecl Hello_World(void) ::: 1774393334640568 - 1774393334645912 ::: 5343 microseconds 
```