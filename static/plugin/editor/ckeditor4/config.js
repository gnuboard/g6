/**
 * @license Copyright (c) 2003-2018, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see https://ckeditor.com/legal/ckeditor-oss-license
 */

//  모바일 체크
if(typeof(g5_is_mobile) == "undefined") g5_is_mobile = false;

var ck_cachequeryMentions = [],
    ck_itemsMentions = null,
    ck_extraPlugins = 'uploadwidget,uploadimage,editorplaceholder,mentions';

function dataFeed( opts, callback ) {
    var data = [];

    if (opts.marker == "@" && opts.query) {
        
        var thisVal = opts.query,
            srcRegex = /<img.*?src=["'](.*?)["']/;
        
        ck_itemsMentions = ck_cachequeryMentions[thisVal];

        if(typeof ck_itemsMentions == "object"){
            callback(ck_itemsMentions);
        } else {
            var data_url = g5_plugin_url+"/mention/q.php";

            $.getJSON( data_url ,{
                s: thisVal
            }, function(json_data) {

                $.each( json_data, function( key, value ){
                    
                    var match = srcRegex.exec(value.img),
                        srcValue = g5_url + "/img/common/icon-chat-m.png";
                    if (match && match[1]) {
                        srcValue = match[1];
                    }
                    var subdata = {
                        id: key + 1,
                        mb_nick: value.mb_nick,
                        img_src: srcValue
                    }

                    data.push(subdata);
                });
                ck_cachequeryMentions[thisVal] = data;
                callback(data);
            });
        }
    } else {
        callback( data );
    }
}

CKEDITOR.editorConfig = function( config ) {
	// 에디터 높이 설정
	if(typeof(editor_height) != "undefined") {
		config.height = editor_height+"px";
	}

	// 언어 설정
	config.language = 'ko';
	// 글꼴관련
	config.font_names = '맑은 고딕;굴림;굴림체;궁서;궁서체;돋움;돋움체;바탕;바탕체;';  // + CKEDITOR.config.font_names;
	config.font_defaultLabel = '맑은 고딕';
	//config.font_defaultLabel = 'Malgun Gothic';
	// 글자크기 출력
	config.fontSize_sizes = '8pt;9pt;10pt;11pt;12pt;14pt;16pt;20pt;24pt;30pt;48pt;60pt;72pt;';

	// 툴바 기능버튼 순서
	config.toolbarGroups = [
		{ name: '1', groups: [ 'styles', 'align', 'basicstyles', 'cleanup' ] },
		{ name: '2', groups: [ 'insertImg', 'insert', 'colors', 'list', 'blocks', 'links', 'mode', 'tools', 'about' ] }
	];

	// 미노출 기능버튼
	if(g5_is_mobile) {
		//--- 모바일 ---//
		config.removeButtons = 'Print,Cut,Copy,Paste,Subscript,Superscript,Anchor,Unlink,ShowBlocks,Undo,Redo,Smiley,Font,Italic,Underline,Strike,BGColor';

        config.toolbarGroups = [
            { name: '1', groups: [ 'styles', 'align', 'basicstyles', 'insertImg', 'colors', 'links', 'mode' ] }
        ];
	} else {
		//--- PC ---//
		config.removeButtons = 'Print,Cut,Copy,Paste,Subscript,Superscript,Anchor,Unlink,ShowBlocks,Undo,Redo,Smiley';
	}

    config.mentions = [{
        feed: dataFeed,
        caseSensitive: true,
        itemTemplate: '<li data-id="{id}">' +
                '<img class="photo" src="{img_src}" widht="20" height="20" />' +
                '<strong class="username">{mb_nick}</strong>' +
            '</li>',
        outputTemplate: '<span class="atwho-inserted">@{mb_nick}</span><span>&nbsp;</span>',
        minChars: 1,
        // pattern: /(?:^|\s)@([가-힣ㄱ-ㅎA-Za-zÀ-ÿ0-9_'.+-]*)$|(?:^|\s)@([^\x00-\xff]*)$/gi
    }];

	/* 이미지 업로드 관련 소스 */
	let up_url = g5_url + "editor/ckeditor4/upload?type=Images";

	// 에디터 구분
	if(typeof(editor_id) != "undefined" && editor_id != "") {
		up_url += "&editor_id="+editor_id;
	}
	// 업로드 경로 - editor_uri
	if(typeof(editor_uri) != "undefined" && editor_uri != "") {
		up_url += "&editor_uri="+editor_uri;
	}
	// 업로드 이미지용 토큰
	if( typeof(editor_form_name) != "undefined" && editor_form_name != "") {
		up_url += "&editor_form_name="+editor_form_name;
	}
    
	// 업로드 페이지 URL 선언
	config.filebrowserImageUploadUrl = up_url;

	// 이미지 다이얼로그 수정 
	CKEDITOR.on('dialogDefinition', function (ev) {
		let dialogName = ev.data.name;
		let dialog = ev.data.definition.dialog;
		let dialogDefinition = ev.data.definition;
		if (dialogName == 'image') {
			dialog.on('show', function (obj) {
				//this.selectPage('Upload'); //업로드텝으로 시작
			});
			dialogDefinition.removeContents('advanced'); // 자세히탭 제거
			dialogDefinition.removeContents('Link'); // 링크탭 제거
			
			var infoTab = dialogDefinition.getContents('info');   
			infoTab.remove('txtHSpace');
			infoTab.remove('txtVSpace');
			infoTab.remove('htmlPreview');	// 미리보기 제거
		}
	});

	// 사용할 플러그인 추가
	// config.extraPlugins = 'uploadwidget,uploadimage,emoji,autogrow,editorplaceholder,mentions';
    config.extraPlugins = ck_extraPlugins;

	// 본문내용 불러들일때 속성유지
	config.allowedContent = true;

	// iOS만 적용
	if(/iPhone|iPad|iPod/i.test(navigator.userAgent) ) {
		// 한글 입력 관련 줄바꿈 과정에서 문제발생하여 적용
		config.removePlugins = 'enterkey';
	}

	if (get_cookie('darkmode') == 'ON') {
		config.contentsCss = [CKEDITOR.getUrl('darkmode.css')];
    }
};
