@0xae1f1be0650fec43;

struct Value {
    # NEED TO DO THIS STILL
        value :union {
            strVal @0 :Text;
            intVal @1 :Int64;
            doubleVal @2 :Float64;
        }
    }

struct Node {
    axis @0 :Text;
    value @1 :List(Value);
    result @2 :List(Float64);
    resultSize @3 :List(Int64);
    children @4 :List(Node);
}