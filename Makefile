CC = gcc
CFLAGS = -std=c99 -O3 -Wall -Wextra
LDFLAGS = -lm

TARGET = mandelbrot
SRCS = main.c mandelbrot.c io_utils.c
OBJS = $(SRCS:.c=.o)

PYTHON = python3
SERIAL_BIN = mandelbrot_serial.bin

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $(OBJS) $(LDFLAGS)

main.o: main.c mandelbrot.h io_utils.h
	$(CC) $(CFLAGS) -c $< -o $@

mandelbrot.o: mandelbrot.c mandelbrot.h
	$(CC) $(CFLAGS) -c $< -o $@

io_utils.o: io_utils.c io_utils.h mandelbrot.h
	$(CC) $(CFLAGS) -c $< -o $@

run: $(TARGET)
	./$(TARGET)

# Auto-comparação da referência serial (sanidade do validador).
validate: $(SERIAL_BIN) validate.py
	$(PYTHON) validate.py $(SERIAL_BIN) $(SERIAL_BIN)

$(SERIAL_BIN): $(TARGET)
	./$(TARGET)

clean:
	rm -f $(OBJS) $(TARGET)
	rm -f *.pgm *.ppm *.bin

.PHONY: all run clean validate
