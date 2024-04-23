

struct Value {
    # NEED TO DO THIS STILL
        value :union {
            str_val @0 :Text;
            int_val @1 :Int64;
            double_val @2 :Float64;
        }
    }

struct Node {
    axis @0 :Text;
    value @1 :List(Value);
    result @2 :List(Float64);
    result_size @3 :List(Int64);
    children @4 :List(Node);
}