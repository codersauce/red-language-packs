#include <iostream>

class Greeter {
public:
    void greet() const {
        std::cout << "Hello from Red!";
    }
};

int main() {
    Greeter{}.greet();
    return 0;
}
