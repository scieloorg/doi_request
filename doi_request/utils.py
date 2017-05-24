def pagination_ruler(limit, total, offset):
    """
    This function returns a list of pagination links according to the given
    definitions.
    """

    ruler = []

    current_index = 0
    for ndx, item in enumerate(range(0, total+limit, limit)):
        page = int((item/limit)) + 1
        if page < 1:
            continue
        current = True if int((offset/limit))+1 == page else False
        if current is True:
            current_index = ndx
        page_offset = item
        start_range = page_offset + 1
        end_range = page_offset + limit
        if end_range < total:
            ruler.append((page, current, page_offset, start_range, end_range))
        else:
            ruler.append((page, current, page_offset, start_range, total))
            break

    if current_index == 1:
        return ruler[current_index-1:current_index+4]

    if current_index == 0:
        return ruler[current_index:current_index+5]

    if current_index+2 == len(ruler):
        return ruler[current_index-3:]

    if current_index+1 == len(ruler):
        return ruler[current_index-4:]

    return ruler[current_index-2:current_index+3]
