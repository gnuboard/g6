var order_stock_check = function() {
    var result = "";
    $.ajax({
        type: "POST",
        url: g6_url+"/shop/ajax.orderstock.php",
        cache: false,
        async: false,
        success: function(data) {
            result = data;
        }
    });
    return result;
}