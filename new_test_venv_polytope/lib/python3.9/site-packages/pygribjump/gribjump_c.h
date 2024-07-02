
// clean cffi-friendly version 

struct gribjump_handle_t;
typedef struct gribjump_handle_t gribjump_handle_t;

struct gribjump_extraction_result_t;
typedef struct gribjump_extraction_result_t gribjump_extraction_result_t;

struct gribjump_extraction_request_t;
typedef struct gribjump_extraction_request_t gribjump_extraction_request_t;

struct gj_axes_t;
typedef struct gj_axes_t gj_axes_t;

int gribjump_new_handle(gribjump_handle_t** gj);
int gribjump_delete_handle(gribjump_handle_t* gj);

int extract_single(gribjump_handle_t* handle, gribjump_extraction_request_t* request, gribjump_extraction_result_t*** results_array, unsigned short* nfields);
int extract(gribjump_handle_t* handle, gribjump_extraction_request_t** requests, unsigned short nrequests, gribjump_extraction_result_t**** results_array, unsigned short** nfields);

int gribjump_new_request(gribjump_extraction_request_t** request, const char* reqstr, const char* rangesstr);
int gribjump_delete_request(gribjump_extraction_request_t* request);
int gribjump_new_result(gribjump_extraction_result_t** result);
int gribjump_result_values(gribjump_extraction_result_t* result, double*** values, unsigned long* nrange, unsigned long** nvalues);
int gribjump_result_values_nocopy(gribjump_extraction_result_t* result, double*** values, unsigned long* nrange, unsigned long** nvalues);
int gribjump_result_mask(gribjump_extraction_result_t* result,  unsigned long long*** masks, unsigned long* nrange, unsigned long** nmasks);
int gribjump_delete_result(gribjump_extraction_result_t* result);
int gribjump_new_axes(gj_axes_t** axes, const char* reqstr, gribjump_handle_t* gj);
int gribjump_axes_keys(gj_axes_t* axes, const char*** keys_out, unsigned long* size);
int gribjump_axes_values(gj_axes_t* axes, const char* key, const char*** values_out, unsigned long* size);
int gribjump_delete_axes(gj_axes_t* axes);

int gribjump_initialise();
