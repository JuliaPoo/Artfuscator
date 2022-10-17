BIN_DIR=../elvm/out

build-ir:
	$(BIN_DIR)/8cc -I../elvm/libc -S $(i).c

run-ir: build-ir
	$(BIN_DIR)/eli $(i).s

build-art: build-ir
	$(BIN_DIR)/elc -art $(i).s > $(i).art.nasm

run-art: build-art
	nasm -f elf32 $(i).art.nasm
	ld -m elf_i386 -o $(i).art.exe $(i).art.o
	./$(i).art.exe

run-art-release: build-art
	nasm -f elf32 $(i).art.nasm
	ld -m elf_i386 --strip-all -o $(i).art.exe $(i).art.o
	./$(i).art.exe

run-art-ir:
	$(BIN_DIR)/elc -art $(i).s > $(i).art.nasm
	nasm -f elf32 $(i).art.nasm
	ld -m elf_i386 -o $(i).art.exe $(i).art.o
	./$(i).art.exe

run-nasm:
	nasm -f elf32 $(i).nasm
	ld -m elf_i386 -o $(i).exe $(i).o
	./$(i).exe

run-nasm-release:
	nasm -f elf32 $(i).nasm
	ld -m elf_i386 --strip-all -o $(i).exe $(i).o
	./$(i).exe
	
clean:
	find . -name "*.s" -type f -delete
	find . -name "*.art.nasm" -type f -delete
	find . -name "*.o" -type f -delete
	find . -name "*.exe" -type f -delete