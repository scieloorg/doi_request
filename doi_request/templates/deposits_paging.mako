<div class="col-sm-4">
  ${_(u'mostrando página')} ${page} de ${total_pages}
</div>
<div class="col-sm-8">
  <ul class="pagination pull-right">
    % if offset > 0:
      <li class="paginate_button previous">
        <a href="/?offset=${offset-limit}">Previous</a>
      </li>
    % else:
      <li class="paginate_button previous disabled">
        <a href="#">Previous</a>
      </li>
    % endif
    % for ppage, pcurrent, poffset, pstart_range, pend_range in pagination_ruler:
    <li class="paginate_button ${'active' if pcurrent is True else ''}">
      <a href="/?offset=${poffset}">${ppage}</a>
    </li>
    % endfor
    % if offset+limit <= total:
      <li class="paginate_button next" id="example2_next">
        <a href="/?offset=${offset+limit}">Next</a>
      </li>
    % else:
      <li class="paginate_button next disabled">
        <a href="#">Next</a>
      </li>
    % endif
  </ul>
</div>