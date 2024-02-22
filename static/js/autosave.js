// 임시 저장하는 시간을 초단위로 설정한다.
var AUTOSAVE_INTERVAL = 60; // 초

// 글의 제목과 내용을 바뀐 부분이 있는지 비교하기 위하여 저장해 놓는 변수
var save_wr_subject = null;
var save_wr_content = null;
var target_editor_id = 'wr_content'
function autosave() {
    $("form#fwrite").each(function () {
        if (typeof getEditorContent === 'function') {
            this.wr_content.value = getEditorContent(target_editor_id);
        }

        if (this.wr_content.value === '' || this.wr_subject.value === '') {
            return false;
        }

        // 변수에 저장해 놓은 값과 다를 경우에만 임시 저장함
        if (save_wr_subject != this.wr_subject.value || save_wr_content != this.wr_content.value) {
            let formData = new FormData();
            formData.append('as_subject', this.wr_subject.value);
            formData.append('as_content', this.wr_content.value);
            formData.append('as_uid', this.uid.value);

            $.ajax({
                url: g6_bbs_url + "/ajax/autosave",
                data: formData,
                type: "POST",
                processData: false,
                contentType: false,
                success: function (res) {
                    if (res) {
                        $("#autosave_count").html(res.count);
                    }
                }
            });
            save_wr_subject = this.wr_subject.value;
            save_wr_content = this.wr_content.value;
        }
    });
}

$(function () {
    // 임시저장된 글 개수를 가져옴
    $.ajax(g6_bbs_url + "/ajax/autosave_count", {
        headers: {"Content-Type": "application/json;"},
        type: "get",
        success: function (result) {
            const countNode = document.querySelector('#autosave_count');
            countNode.textContent = parseInt(result.count);
        }
    });
    
    if (g6_is_member) {
        setInterval(autosave, AUTOSAVE_INTERVAL * 1000);
    }
    const autosavePop = $("#autosave_pop");
    // 임시저장된 글목록을 가져옴
    $("#btn_autosave").click(function () {
        if (autosavePop.is(":hidden")) {
            $.ajax(g6_bbs_url + "/ajax/autosave_list", {
                headers: {
                    "Content-Type": "application/json;"
                },
                type: "get",
                success: function (data) {
                    const list = autosavePop.find("ul");
                    list.empty();
                    if (data.length > 0) {
                        $(data).each(function (i, item) {

                            let datetime = new Date(item.as_datetime).toLocaleDateString(navigator.language, {
                                hour: "2-digit",
                                minute: "numeric"
                            });
                            list.append('<li data-as_id=' + item.as_id + '>' +
                                '<a href="#none" class="autosave_load">' + item.as_subject + '</a>' +
                                '<span>' + datetime + ' <button type="button" name="as_id" value="' +
                                item.as_id + '" class="autosave_del">삭제</input></span></li>'
                            );
                        });
                    }
                }
            });

            autosavePop.show();
        } else {
            autosavePop.hide();
        }
    });

    // 임시저장된 글 제목과 내용을 가져와서 제목과 내용 입력박스에 노출해 줌
    $(document).on("click", ".autosave_load", function () {
        const $li = $(this).parents("li");
        const as_id = $li.data("as_id");
        $.ajax(g6_bbs_url + "/ajax/autosave_load/" + as_id, {
            success: function (data) {
                const subject = data.as_subject;
                const content = data.as_content;
                document.querySelector('#wr_subject').value = subject;
                if (typeof setEditorContent === "function") {
                    setEditorContent('wr_content', content);
                }
            }
        });
        $("#autosave_pop").hide();
    });

    $(document).on("click", ".autosave_del", function () {
        const $li = $(this).parents("li");
        const as_id = $li.data("as_id");
        $.ajax(g6_bbs_url + "/ajax/autosave/" + as_id, {
            headers: {
                "Content-Type": "application/json;"
            },
            type: "DELETE",
            success: function (data) {
                const countNode = document.querySelector('#autosave_count');
                countNode.textContent = parseInt(countNode.textContent) - 1;
                $li.remove();
            },
            error: function (res) {
                alert(res.responseJSON.detail);
            }
        });
    });

    $(".autosave_close").click(function () {
        $("#autosave_pop").hide();
    });
});
