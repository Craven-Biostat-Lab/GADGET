// display a message
function flash(message)
{
    $("#flash").html(message).fadeTo(400, 1);
}

function hideflash()
{
    $("#flash").fadeTo(300, 0);
}

function spin()
{
    flash('<img src="/static/spinner.gif" />');
}

$(document).ready(function() {
    stripetables();
    
    $("#flash")
    .click(function() {
        $(this).hide();
    })
    .mouseover(function() {
        if ($(this).is(":visible")) $(this).fadeTo(200, 0.3);
    })
    .mouseout(function() {
        if ($(this).is(":visible")) $(this).fadeTo(200, 1);
    });
    
    
});

function stripetables() {
    $("table.results tr").removeClass("alt");
    $("table.results tr:even").addClass("alt");

    $("table.results tr")
    .mouseover(function() {
        $(this).addClass("over");
    })
    .mouseout(function() {
        $(this).removeClass("over");
    });
}
