function shutdown(){
        $.ajax({
                url:"/shutdown",
                success: function(data) {
                        //alert('Server has been shutdown.');
                        $('#console_text').text('Server has been shutdown');
                }
        });
}
