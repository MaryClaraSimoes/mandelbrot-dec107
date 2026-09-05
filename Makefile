CC = gcc
CFLAGS = -std=c99 -O3 -Wall -Wextra
LDFLAGS = 

TARGET = mandelbrot
SRCS = main.c mandelbrot.c
OBJS = $(SRCS:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $(OBJS) $(LDFLAGS)

%.o: %.c mandelbrot.h
	$(CC) $(CFLAGS) -c $< -o $@

run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(OBJS) $(TARGET)

.PHONY: all run clean
