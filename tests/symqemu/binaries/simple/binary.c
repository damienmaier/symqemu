#include <stdio.h>

int main(int argc, char *argv[]) {

    if (argc != 2) {
        puts("ERROR: You need one argument.");
        return 1;
    }

    FILE* file_stream = fopen(argv[1], "r");

    if (!file_stream) {
        puts("ERROR: Could not open file.");
        return 1;
    }

    char input = getc(file_stream);

    if (input == 'z') {
        puts("you win!");
    } else {
        puts("you lose!");
    }

}