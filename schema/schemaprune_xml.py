from types import *
import sys
from xml.dom.minidom import parse
import xml.dom.minidom

#Temporarily maintaining a static list
enabled_features = []
local_features = []
MAX_FEATURES = 50

def check_delete_object(objname):
    local_features = ['']*MAX_FEATURES
    feature_list = objname.getElementsByTagName("feature_list")
    if (feature_list):
        print("len: %s" % len(feature_list))
        features = objname.getElementsByTagName("feature")
        for i in range(0, (len(feature_list))):
            feature = features[i]
            print("%s" % feature.childNodes[0].nodeValue)
            local_features[i] = str(feature.childNodes[0].nodeValue)

        for i in range(0, len(feature_list)):
            print("local_feature = %s" % local_features[i])

        if bool(set(local_features) & set(enabled_features)):
            print("There is at least 1 feature in the feature_list that has been enabled. Cannot delete object")
            return False
        else:
            return True
    else:
        #This is base object. Cannot delete it
        return False


def delete_object(objname):
    parent = objname.parentNode
    print("parent = %s" % parent)
    parent.removeChild(objname)


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

# read the xml ovs schema
DOMTree = xml.dom.minidom.parse(sys.argv[1])

# Walk the XML file containing the schema in XML format & delete items
# corresponding to features that have not been enabled
tables = DOMTree.getElementsByTagName("table")
for table in tables:
    del_table = del_group = del_column = False

    print("table: %s" % table.getAttribute("name"))
    del_table = check_delete_object(table)

    groups = table.getElementsByTagName("group")
    for group in groups:
        print("group: %s" % group.getAttribute("title"))
        del_group = check_delete_object(group)

        columns = group.getElementsByTagName("column")
        for column in columns:
            print("column: %s; key: %s" % (column.getAttribute("name"), column.getAttribute("key")))

            del_column = check_delete_object(column)
            if (del_column == True):
                print("column %s; key: %s can be deleted" % (column.getAttribute("name"), column.getAttribute("key")))
                delete_object(column)
            else:
                print("column %s; key: %s cannot be deleted" % (column.getAttribute("name"), column.getAttribute("key")))
                #del_group = False

        if (del_group == True):
            print("group %s can be deleted" % group.getAttribute("title"))
            delete_object(group)
        else:
            print("group %s cannot be deleted" % group.getAttribute("title"))
            #del_table = False

    #Now let's check the remaining columns
    columns = table.getElementsByTagName("column")
    for column in columns:
        print("column: %s; key: %s" % (column.getAttribute("name"), column.getAttribute("key")))
        del_column = check_delete_object(column)
        if (del_column == True):
            print("column %s; key: %s can be deleted" % (column.getAttribute("name"), column.getAttribute("key")))
            delete_object(column)
        else:
            print("column %s; key: %s cannot be deleted" % (column.getAttribute("name"), column.getAttribute("key")))
            #del_table = False

    if (del_table == True):
        print("table %s can be deleted" % table.getAttribute("name"))
        delete_object(table)
    else:
        print("table %s cannot be deleted" % table.getAttribute("name"))


# Generate the output schema file
file_handle = open(sys.argv[2], "w")
DOMTree.writexml(file_handle)
file_handle.close()
