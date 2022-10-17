ELVM_DIR=./elvm/

check_defined = \
    $(strip $(foreach 1,$1, \
        $(call __check_defined,$1,$(strip $(value 2)))))
__check_defined = \
    $(if $(value $1),, \
        $(error Undefined $1$(if $2, ($2))$(if $(value @), \
                required by target `$@')))

%:
	@:$(call check_defined, IMG)
	mkdir -p build
	$(ELVM_DIR)/out/8cc -I$(ELVM_DIR)/libc -o build/$@.s -S $@.c
	$(ELVM_DIR)/out/elc -art build/$@.s > build/$@.art.nasm
	python3 -m artfuscator -i $(IMG) build/$@.art.nasm
	nasm -f elf32 -o build/$@.art.o build/$@.art.nasm
	mkdir -p dist
	ld -m elf_i386 --strip-all -o dist/$@.art build/$@.art.o

clean:
	@echo owo
#	rm -r build
#	rm -r dist