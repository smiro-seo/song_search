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

function clear_input() {
    fetch("/clear_input", {
        method: "POST",
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
        } else {
            $('#limit-range-kw').attr('disabled', true);
            $('#limit-range-kw-txt').attr('disabled', true);
        }

    });
    
    $('#check-offset').on('change', function(){

        let able = $('#check-offset').is(':checked');
        if(able) {
            $('#offset-range').attr('disabled', false);
            $('#offset-range-txt').attr('disabled', false);

            $('#lower-limit').text('');
            $('#lower-limit').text($('#offset-range').val());
            $('#upper-limit').text('');
            $('#upper-limit').text(parseFloat($('#offset-range').val()) + parseFloat($('#limit-range-kw').val()));

        } else {
            $('#offset-range').attr('disabled', true);
            $('#offset-range-txt').attr('disabled', true);

            $('#lower-limit').text('');
            $('#lower-limit').text('0');
            $('#upper-limit').text('');
            $('#upper-limit').text($('#limit-range-kw').val());
        }

    });
    
    $('#limit-range-kw').on('change', function(){

        let value = $('#limit-range-kw').val();
        $('#limit-range-kw-txt').val(value);

        $('#upper-limit').text('');
        $('#upper-limit').text(parseFloat(value) + parseFloat($('#offset-range').val()));

    });
    $('#limit-range-kw-txt').on('change', function(){

        let value = $('#limit-range-kw-txt').val();
        $('#limit-range-kw').val(value);

        $('#upper-limit').text('');
        $('#upper-limit').text(parseFloat(value) + parseFloat($('#offset-range').val()));

    });

    $('#offset-range').on('change', function(){

        let value = $('#offset-range').val();
        $('#offset-range-txt').val(value);

        $('#lower-limit').text('');
        $('#lower-limit').text(value);
        $('#upper-limit').text('');
        $('#upper-limit').text(parseFloat(value) + parseFloat($('#limit-range-kw').val()));

    });
    $('#offset-range-txt').on('change', function(){

        let value = $('#offset-range-txt').val();
        $('#offset-range').val(value);

        $('#lower-limit').text('');
        $('#lower-limit').text(value);
        $('#upper-limit').text('');
        $('#upper-limit').text(parseFloat(value) + parseFloat($('#limit-range-kw').val()));

    });
})