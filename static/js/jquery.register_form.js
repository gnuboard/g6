function valid_register_field(field, mb_id) {
    let result = "";
    $.ajax({
        type: "GET",
        url: g6_bbs_url + "/register/validate/" + field + "?value=" + encodeURIComponent(mb_id),
        cache: false,
        async: false,
        success: function(data) {
            result = data;
        }
    });

    return result;
}
