function check_all(f)
{
    var chk = document.getElementsByName("chk[]");

    for (i=0; i<chk.length; i++)
        chk[i].checked = f.chkall.checked;
}

function btn_check(f, act)
{
    if (act == "update") // 선택수정
    {
        f.action = list_update_php;
        str = "수정";
    }
    else if (act == "delete") // 선택삭제
    {
        f.action = list_delete_php;
        str = "삭제";
    }
    else
        return;

    var chk = document.getElementsByName("chk[]");
    var bchk = false;

    for (i=0; i<chk.length; i++)
    {
        if (chk[i].checked)
            bchk = true;
    }

    if (!bchk)
    {
        alert(str + "할 자료를 하나 이상 선택하세요.");
        return;
    }

    if (act == "delete")
    {
        if (!confirm("선택한 자료를 정말 삭제 하시겠습니까?"))
            return;
    }

    f.submit();
}

function is_checked(elements_name)
{
    var checked = false;
    var chk = document.getElementsByName(elements_name);
    for (var i=0; i<chk.length; i++) {
        if (chk[i].checked) {
            checked = true;
        }
    }
    return checked;
}

function delete_confirm(el)
{
    if (confirm("한번 삭제한 자료는 복구할 방법이 없습니다.\n\n정말 삭제하시겠습니까?")) {
        var token = generate_token();

        var url = el.href;
        if (url.indexOf("?") > -1) {
            url += "&token=" + token;
        } else {
            url += "?token=" + token;
        }

        el.href = url;

        return true;
    } else {
        return false;
    }
}

function delete_confirm2(msg)
{
    if(confirm(msg))
        return true;
    else
        return false;
}

// 삭제요청 임시 함수
function delete_confirm3(element)
{
    if(confirm("한번 삭제한 자료는 복구할 방법이 없습니다.\n\n정말 삭제하시겠습니까?")) {
        // DELETE 요청을 생성하고 서버로 보냅니다.
        token = generate_token();
        if (token) {
            $.ajax({
                type: "DELETE",
                url: element.href + "?token=" + token,
                success: function(data) {
                    if (data.message) {
                        alert(data.message);
                    }
                    location.reload();                  
                },
                error: function(xhr, textStatus, errorThrown) {
                    responese = JSON.parse(xhr.responseText);
                    alert(responese.message);
                }
            });
        }
    }
    return false;
}
