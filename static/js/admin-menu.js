document.addEventListener('DOMContentLoaded', function() {
    var hide_menu = false;
    var mouse_event = false;
    var oldX = oldY = 0;

    document.addEventListener('mousemove', function(e) {
        if(oldX == 0) {
            oldX = e.pageX;
            oldY = e.pageY;
        }

        if(oldX != e.pageX || oldY != e.pageY) {
            mouse_event = true;
        }
    });

    document.addEventListener('mouseover', function(e) {
        if(e.target.matches('.gnb_1dli > a') && mouse_event) {
            document.getElementById('hd').classList.add('hd_zindex');
            var gnb_1dli = document.querySelectorAll('.gnb_1dli');
            gnb_1dli.forEach(function(elem) {
                elem.classList.remove('gnb_1dli_over', 'gnb_1dli_over2', 'gnb_1dli_on');
            });
            e.target.parentNode.classList.add('gnb_1dli_over', 'gnb_1dli_on');
            menu_rearrange(e.target.parentNode);
            hide_menu = false;
        }
    });

    document.addEventListener('mouseout', function(e) {
        if(e.target.matches('.gnb_1dli > a') || e.target.matches('.gnb_2dli')) {
            hide_menu = true;
        }
    });

    document.addEventListener('focusin', function(e) {
        if(e.target.matches('.gnb_1dli > a') || e.target.matches('.gnb_2da')) {
            document.getElementById('hd').classList.add('hd_zindex');
            var gnb_1dli = document.querySelectorAll('.gnb_1dli');
            gnb_1dli.forEach(function(elem) {
                elem.classList.remove('gnb_1dli_over', 'gnb_1dli_over2', 'gnb_1dli_on');
            });
            e.target.parentNode.classList.add('gnb_1dli_over', 'gnb_1dli_on');
            menu_rearrange(e.target.parentNode);
            hide_menu = false;
        }
    });

    document.addEventListener('focusout', function(e) {
        if(e.target.matches('.gnb_1dli > a') || e.target.matches('.gnb_2da')) {
            hide_menu = true;
        }
    });

    document.querySelectorAll('#gnb_1dul>li').forEach(function(elem) {
        elem.addEventListener('mouseleave', function() {
            submenu_hide();
        });
    });
    
    document.addEventListener('click', function(e) {
        if(hide_menu) {
            submenu_hide();
        }
    });

    document.addEventListener('focusin', function(e) {
        if(hide_menu) {
            submenu_hide();
        }
    });
});

function submenu_hide() {
    document.getElementById('hd').classList.remove('hd_zindex');
    var gnb_1dli = document.querySelectorAll('.gnb_1dli');
    gnb_1dli.forEach(function(elem) {
        elem.classList.remove('gnb_1dli_over', 'gnb_1dli_over2', 'gnb_1dli_on');
    });
}

function menu_rearrange(el)
{
    var width = document.getElementById('gnb_1dul').offsetWidth;
    var left = w1 = w2 = 0;
    var gnb_1dli = document.querySelectorAll('.gnb_1dli');
    var idx = Array.prototype.indexOf.call(gnb_1dli, el);
    var max_menu_count = 0;

    for(var i = 0; i <= idx; i++) {
        var currentEl = gnb_1dli[i];
        w1 = currentEl.offsetWidth;

        if(currentEl.querySelector('.gnb_2dul'))
            w2 = currentEl.querySelector('.gnb_2dli > a').offsetWidth;
        else
            w2 = w1;

        if((left + w2) > width) {
            if(max_menu_count == 0)
                max_menu_count = i + 1;
        }

        if(max_menu_count > 0 && (idx + 1) % max_menu_count == 0) {
            el.classList.remove('gnb_1dli_over');
            el.classList.add('gnb_1dli_over2');
            left = 0;
        } else {
            left += w1;
        }
    }
}
