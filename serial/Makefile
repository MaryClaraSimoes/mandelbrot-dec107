CC      = gcc
CFLAGS  = -std=c99 -O3 -Wall -Wextra
LDFLAGS = -lm

COMMON_DIR = ../common
INCLUDES   = -I$(COMMON_DIR)

TARGET = mandelbrot_seq

# Fontes: as compartilhadas em common/ + as específicas desta versão
COMMON_SRCS = $(COMMON_DIR)/common.c $(COMMON_DIR)/io_utils.c
LOCAL_SRCS  = main.c mandelbrot_compute.c

OBJS = $(notdir $(COMMON_SRCS:.c=.o)) $(LOCAL_SRCS:.c=.o)

vpath %.c $(COMMON_DIR)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $(OBJS) $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(OBJS) $(TARGET)
	rm -f *.pgm *.ppm *.bin

.PHONY: all run clean
