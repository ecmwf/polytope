

struct Value {
    # NEED TO DO THIS STILL
        oneof value {
            string str_val = 1;
            int64 int_val = 2;
            double double_val = 3;
        }
    }

struct Node {
    axis @0 :Text;
    value @1 :List(Value);
    result @2 :List(Float64);
    repeated int64 result_size @3 = 4;
    repeated Node children = 5;
}