function total(items) {
    var sum = 0;
    for (var i = 0; i < items.length; i++) {
        sum = sum + items[i].price * items[i].qty;
    }
    return sum;
}
