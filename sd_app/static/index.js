function delete_row(idx, table) {
    if(table == "input") {
        fetch("/delete_row", {
            method: "POST",
            body: JSON.stringify({ idx: idx }),
        }).then((_res) => {
            window.location.href = "/search";
        });
    } else if(table=="history"){
        fetch("/delete_search", {
            method: "POST",
            body: JSON.stringify({ idx: idx }),
        }).then((_res) => {
            window.location.href = "/history";
        });
    }
    
};

function repeat_search(keyword_json) {
    fetch("/repeat_search", {
        method: "POST",
        body: JSON.stringify({ keyword: keyword_json }),
    }).then((_res) => {
        window.location.href = "/search";
    });
}

function clear_table(what_to_clear) {
    fetch("/clear", {
        method: "POST",
        body: JSON.stringify({ what_to_clear: what_to_clear })
    }).then((_res) => {
        window.location.href = "/search";
    });
};

$(document).ready(function() {
    $('#check-limit-kw').on('change', function(){

        let able = $('#check-limit-kw').is(':checked');
        if(able) {
            $('#limit-range-kw').attr('disabled', false);
            $('#limit-range-kw-txt').attr('disabled', false);

            $('#upper-limit').text('');
            $('#upper-limit').text(parseFloat($('#lower-limit').text()) + parseFloat($('#limit-range-kw-txt').val()));
        } else {
            $('#limit-range-kw').attr('disabled', true);
            $('#limit-range-kw-txt').attr('disabled', true);

            $('#upper-limit').text('');
            $('#upper-limit').text('infinity');
        }

    });
    
    $('#check-offset').on('change', function(){

        let able = $('#check-offset').is(':checked');
        if(able) {
            $('#offset-range').attr('disabled', false);
            $('#offset-range-txt').attr('disabled', false);

            $('#lower-limit').text('');
            $('#lower-limit').text(parseFloat($('#offset-range-txt').val())+1);
            if($('#upper-limit').text() != 'infinity'){
                $('#upper-limit').text('');
                $('#upper-limit').text(parseFloat($('#offset-range-txt').val()) + parseFloat($('#limit-range-kw-txt').val()));
            }

        } else {
            $('#offset-range').attr('disabled', true);
            $('#offset-range-txt').attr('disabled', true);

            $('#lower-limit').text('');
            $('#lower-limit').text('1');
            if($('#upper-limit').text() != 'infinity'){
                $('#upper-limit').text('');
                $('#upper-limit').text(parseFloat($('#limit-range-kw-txt').val()));
            }
        }

    });
    
    $('#limit-range-kw').on('change', function(){

        let value = $('#limit-range-kw').val();
        $('#limit-range-kw-txt').val(value);

        $('#upper-limit').text('');
        $('#upper-limit').text(parseFloat(value) + parseFloat($('#offset-range-txt').val()));

    });
    $('#limit-range-kw-txt').on('change', function(){

        let value = $('#limit-range-kw-txt').val();
        $('#limit-range-kw').val(value);

        $('#upper-limit').text('');
        $('#upper-limit').text(parseFloat(value) + parseFloat($('#offset-range-txt').val()));

    });

    $('#offset-range').on('change', function(){

        let value = $('#offset-range').val();
        $('#offset-range-txt').val(value);

        $('#lower-limit').text('');
        $('#lower-limit').text(parseFloat(value) + 1);
        $('#upper-limit').text('');
        $('#upper-limit').text(parseFloat(value) + parseFloat($('#limit-range-kw-txt').val()));

    });
    $('#offset-range-txt').on('change', function(){

        let value = $('#offset-range-txt').val();
        $('#offset-range').val(value);

        $('#lower-limit').text('');
        $('#lower-limit').text(parseFloat(value) + 1);
        $('#upper-limit').text('');
        $('#upper-limit').text(parseFloat(value) + parseFloat($('#limit-range-kw-txt').val()));

    });
})