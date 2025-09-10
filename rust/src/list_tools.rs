pub fn bisect_left_cmp<T, F>(arr: &[T], val: &T, mut cmp: F) -> isize
where
    F: FnMut(&T, &T) -> bool,
{
    let mut left: isize = -1;
    let mut right: isize = arr.len() as isize;

    while right - left > 1 {
        let e = (left + right) >> 1;
        let elem = &arr[e as usize];

        if cmp(elem, val) {
            left = e;
        } else {
            right = e;
        }
    }

    left
}
