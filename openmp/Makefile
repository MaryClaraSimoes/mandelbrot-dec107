CC      = gcc
CFLAGS  = -std=c99 -O3 -Wall -Wextra -fopenmp
LDFLAGS = -lm -fopenmp

COMMON_DIR = ../common
INCLUDES   = -I$(COMMON_DIR)

TARGET = mandelbrot_omp

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

# Exemplo de execução com política de escalonamento configurável em runtime
# (requer schedule(runtime) no pragma dentro de mandelbrot_compute.c)
run-dynamic: $(TARGET)
	OMP_SCHEDULE="dynamic,16" ./$(TARGET)

run-guided: $(TARGET)
	OMP_SCHEDULE="guided,16" ./$(TARGET)

run-static: $(TARGET)
	OMP_SCHEDULE="static" ./$(TARGET)

clean:
	rm -f $(OBJS) $(TARGET)
	rm -f *.pgm *.ppm *.bin

.PHONY: all run run-dynamic run-guided run-static clean
