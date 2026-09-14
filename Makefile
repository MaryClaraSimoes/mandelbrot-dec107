PYTHON = python3

.PHONY: all serial openmp run-serial run-openmp validate clean

all: serial openmp

serial:
	$(MAKE) -C serial

openmp:
	$(MAKE) -C openmp

run-serial: serial
	$(MAKE) -C serial run

run-openmp: openmp
	$(MAKE) -C openmp run

# Roda as duas versões e compara as saídas binárias (corretude, Secao 5.5)
validate: run-serial run-openmp validate.py
	$(PYTHON) validate.py serial/mandelbrot_serial.bin openmp/mandelbrot_omp.bin

clean:
	$(MAKE) -C serial clean
	$(MAKE) -C openmp clean
