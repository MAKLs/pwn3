CC=g++
CFLAGS= -g -fPIC
LDFLAGS= -shared

TARGET = build/pwn3.so
SOURCES = src/pwn3.cpp
OBJECTS = $(SOURCES:.cpp=.o)

%.o: %.cpp %.h
	$(CC) -c -o $@ $< $(CFLAGS)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $(TARGET) $(OBJECTS)

clean:
	rm $(OBJECTS)