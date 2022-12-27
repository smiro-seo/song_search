function delete_row(idx) {
    fetch("/delete_row", {
        method: "POST",
        body: JSON.stringify({ idx: idx }),
    }).then((_res) => {
        window.location.href = "/search";
    });
};

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
    
    $('#check-limit').on('change', function(){

        let able = $('#check-limit').is(':checked');
        if(able) {
            $('#limit-range').attr('disabled', false);
            $('#limit-range-txt').attr('disabled', false);
        } else {
            $('#limit-range').attr('disabled', true);
            $('#limit-range-txt').attr('disabled', true);
        }

    });
    
    $('#limit-range-kw').on('change', function(){

        let value = $('#limit-range-kw').val();
        $('#limit-range-kw-txt').val(value);

    });
    $('#limit-range-kw-txt').on('change', function(){

        let value = $('#limit-range-kw-txt').val();
        $('#limit-range-kw').val(value);

    });

    $('#limit-range').on('change', function(){

        let value = $('#limit-range').val();
        $('#limit-range-txt').val(value);

    });
    $('#limit-range-txt').on('change', function(){

        let value = $('#limit-range-txt').val();
        $('#limit-range').val(value);

    });
})