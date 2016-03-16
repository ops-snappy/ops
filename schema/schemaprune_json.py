from types import *
import json
import sys

#Temporarily maintaining a static list
enabled_features = []

if __name__ == '__main__':
    exit

# sanitize the arguments
if len(sys.argv) < 3:
    print("Error: Script needs 2 argument (input-schema output-schema)")
    sys.exit(0)

# Create enabled_feature_list
# Here we'll go thru the IMAGE_FEATURES variable & create the list.
# For now we're testing with the following static list
enabled_features = ["bgp", "ntp", "ntp_client"]

# read the json ovs schema
with open(sys.argv[1]) as x:
    fs = x.read()
    ovsschema =  json.loads(fs)

# Walk the JSON file containing the schema in JSON format & delete items
# corresponding to features that have not been enabled
tables = ovsschema['tables']
for table in tables.keys():
    print("table = %s" % table)
    del_table = del_column = del_enum = False

    table_data = tables[table]
    if 'feature_list' in table_data:
        print("table = %s" % table)
        features = table_data['feature_list']
        print("features = %s" % features)

        #if ((0 == cmp(features.sort(), enabled_features.sort())) or (set(features) < set(enabled_features))):
        if bool(set(features) & set(enabled_features)):
            print("There is at least 1 feature in the feature_list that has been enabled")
        else:
            del_table = True
            print("Table %s can be deleted" % table)

    if 'columns' in table_data:
        columns = table_data['columns']
        for column in columns.keys():
            print("column = %s" % column)
            column_data = columns[column]
            if 'feature_list' in column_data:
                print("table = %s; column = %s" % (table, column))
                features = column_data['feature_list']
                print("features = %s" % features)
                if bool(set(features) & set(enabled_features)):
                    print("There is at least 1 feature in the feature_list that has been enabled")
                    del_table = False
                else:
                    del_column = True
                    print("table %s column %s can be deleted" % (table, column))
                    #columns.pop(column, None)
                    #del_column = False

            if 'type' in column_data:
                type_data = column_data['type']
                print("type_data = %s" % type_data)
                if 'key' in type_data:
                    key_data = type_data['key']
                    print("key_data = %s" % key_data)
                    if 'enum' in key_data:
                        enum_data = key_data['enum']
                        print("enum_data = %s" % enum_data)
                        if 'set' in enum_data:
                            enum_index = -1
                            for elem in enum_data[1]:
                                enum_index += 1
                                print("enum = %s" % elem)
                                if type(elem) is DictType:
                                    if 'feature_list' in elem:
                                        features = elem['feature_list']
                                        print("features = %s" % features)
                                        if bool(set(features) & set(enabled_features)):
                                            print("There is at least 1 feature in the feature_list that has been enabled")
                                            del_column = False
                                            del_table = False
                                        else:
                                            del_enum = True
                                            print("table %s column %s enum %s can be deleted" % (table, column, elem))
                                            #enum_data.pop(elem, None)
                                            enum_data[1].pop(enum_index)
                                            del_enum = False

            if (del_column == True):
                columns.pop(column, None)
                del_column = False

    if (del_table == True):
        tables.pop(table, None)

# Generate the output schema file
with open(sys.argv[2], 'w') as fo:
    json.dump(ovsschema, fo, sort_keys = True, indent=4, separators=(',', ': '))
    fo.write('\n')
