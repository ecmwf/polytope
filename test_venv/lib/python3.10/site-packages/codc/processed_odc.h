const int ODC_INTEGERS_AS_DOUBLES = 1;
const int ODC_INTEGERS_AS_LONGS = 2;
int odc_initialise_api();
int odc_integer_behaviour(int integerBehaviour);
int odc_version(const char **version);
int odc_vcs_version(const char **version);
enum OdcErrorValues
{
  ODC_SUCCESS = 0,
  ODC_ITERATION_COMPLETE = 1,
  ODC_ERROR_GENERAL_EXCEPTION = 2,
  ODC_ERROR_UNKNOWN_EXCEPTION = 3
};
const char *odc_error_string(int err);
typedef void (*odc_failure_handler_t)(void *context, int error_code);
int odc_set_failure_handler(odc_failure_handler_t handler, void *context);
enum OdcColumnType
{
  ODC_IGNORE = 0,
  ODC_INTEGER = 1,
  ODC_REAL = 2,
  ODC_STRING = 3,
  ODC_BITFIELD = 4,
  ODC_DOUBLE = 5
};
int odc_column_type_count(int *count);
int odc_column_type_name(int type, const char **type_name);
int odc_set_missing_integer(long missing_integer);
int odc_set_missing_double(double missing_double);
int odc_missing_integer(long *missing_value);
int odc_missing_double(double *missing_value);
struct odc_reader_t;
typedef struct odc_reader_t odc_reader_t;
int odc_open_path(odc_reader_t **reader, const char *filename);
int odc_open_file_descriptor(odc_reader_t **reader, int fd);
int odc_open_buffer(odc_reader_t **reader, const void *data, long length);
typedef long (*odc_stream_read_t)(void *context, void *buffer, long length);
int odc_open_stream(odc_reader_t **reader, void *context, odc_stream_read_t stream_proc);
int odc_close(const odc_reader_t *reader);
struct odc_frame_t;
typedef struct odc_frame_t odc_frame_t;
int odc_new_frame(odc_frame_t **frame, odc_reader_t *reader);
int odc_free_frame(const odc_frame_t *frame);
int odc_next_frame(odc_frame_t *frame);
int odc_next_frame_aggregated(odc_frame_t *frame, long maximum_rows);
int odc_copy_frame(odc_frame_t *source_frame, odc_frame_t **copy);
int odc_frame_row_count(const odc_frame_t *frame, long *count);
int odc_frame_column_count(const odc_frame_t *frame, int *count);
int odc_frame_column_attributes(const odc_frame_t *frame, int col, const char **name, int *type, int *element_size, int *bitfield_count);
int odc_frame_bitfield_attributes(const odc_frame_t *frame, int col, int entry, const char **name, int *offset, int *size);
int odc_frame_properties_count(const odc_frame_t *frame, int *nproperties);
int odc_frame_property_idx(const odc_frame_t *frame, int idx, const char** key, const char** value);
int odc_frame_property(const odc_frame_t* frame, const char* key, const char** value);
struct odc_decoder_t;
typedef struct odc_decoder_t odc_decoder_t;
int odc_new_decoder(odc_decoder_t **decoder);
int odc_free_decoder(const odc_decoder_t *decoder);
int odc_decoder_defaults_from_frame(odc_decoder_t *decoder, const odc_frame_t *frame);
int odc_decoder_set_column_major(odc_decoder_t *decoder, _Bool columnMajor);
int odc_decoder_set_row_count(odc_decoder_t *decoder, long nrows);
int odc_decoder_row_count(const odc_decoder_t *decoder, long *nrows);
int odc_decoder_set_data_array(odc_decoder_t *decoder, void *data, long width, long height, _Bool columnMajor);
int odc_decoder_data_array(const odc_decoder_t *decoder, const void **data, long *width, long *height, _Bool *columnMajor);
int odc_decoder_add_column(odc_decoder_t *decoder, const char *name);
int odc_decoder_column_count(const odc_decoder_t *decoder, int *count);
int odc_decoder_column_set_data_size(odc_decoder_t *decoder, int col, int element_size);
int odc_decoder_column_set_data_array(odc_decoder_t *decoder, int col, int element_size, int stride, void *data);
int odc_decoder_column_data_array(const odc_decoder_t *decoder, int col, int *element_size, int *stride, const void **data);
int odc_decode(odc_decoder_t *decoder, const odc_frame_t *frame, long *rows_decoded);
int odc_decode_threaded(odc_decoder_t *decoder, const odc_frame_t *frame, long *rows_decoded, int nthreads);
struct odc_encoder_t;
typedef struct odc_encoder_t odc_encoder_t;
int odc_new_encoder(odc_encoder_t **encoder);
int odc_free_encoder(const odc_encoder_t *encoder);
int odc_encoder_add_property(odc_encoder_t *encoder, const char *key, const char *value);
int odc_encoder_set_row_count(odc_encoder_t *encoder, long nrows);
int odc_encoder_set_rows_per_frame(odc_encoder_t *encoder, long rows_per_frame);
int odc_encoder_set_data_array(odc_encoder_t *encoder, const void *data, long width, long height, int columnMajorWidth);
int odc_encoder_add_column(odc_encoder_t *encoder, const char *name, int type);
int odc_encoder_column_set_data_size(odc_encoder_t *encoder, int col, int element_size);
int odc_encoder_column_set_data_array(odc_encoder_t *encoder, int col, int element_size, int stride, const void *data);
int odc_encoder_column_add_bitfield(odc_encoder_t *encoder, int col, const char *name, int nbits);
typedef long (*odc_stream_write_t)(void *context, const void *buffer, long length);
int odc_encode_to_stream(odc_encoder_t *encoder, void *context, odc_stream_write_t write_fn, long *bytes_encoded);
int odc_encode_to_file_descriptor(odc_encoder_t *encoder, int fd, long *bytes_encoded);
int odc_encode_to_buffer(odc_encoder_t *encoder, void *buffer, long length, long *bytes_encoded);
