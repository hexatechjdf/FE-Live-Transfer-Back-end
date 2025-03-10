from jsonpath_ng import jsonpath, parse


def get_id_value_pair_using_jsonpath(data, id_to_find):
    jsonpath_expr = parse('$..id')
    matches = jsonpath_expr.find(data)
    for match in matches:
        if match.value == id_to_find:
            
            index = matches.index(match)  
            return {id_to_find: data[index]['value']}

    return None
