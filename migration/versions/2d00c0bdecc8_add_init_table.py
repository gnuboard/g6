"""Added table

Revision ID: 2d00c0bdecc8
Revises: 
Create Date: 2023-10-05 09:55:19.678281

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d00c0bdecc8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('g6_board',
    sa.Column('bo_table', sa.String(length=20), nullable=False),
    sa.Column('gr_id', sa.String(length=255), nullable=False),
    sa.Column('bo_subject', sa.String(length=255), nullable=False),
    sa.Column('bo_mobile_subject', sa.String(length=255), nullable=False),
    sa.Column('bo_device', sa.Enum('both', 'pc', 'mobile'), nullable=False),
    sa.Column('bo_admin', sa.String(length=255), nullable=False),
    sa.Column('bo_list_level', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_read_level', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_write_level', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_reply_level', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_comment_level', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_upload_level', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_download_level', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_html_level', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_link_level', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_count_delete', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_count_modify', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_read_point', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_write_point', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_comment_point', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_download_point', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_category', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_category_list', sa.Text(), nullable=False),
    sa.Column('bo_use_sideview', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_file_content', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_secret', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_dhtml_editor', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_select_editor', sa.String(length=50), nullable=False),
    sa.Column('bo_use_rss_view', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_good', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_nogood', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_name', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_signature', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_ip_view', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_list_view', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_list_file', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_list_content', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_table_width', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_subject_len', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_mobile_subject_len', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_page_rows', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_mobile_page_rows', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_new', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_hot', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_image_width', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_skin', sa.String(length=255), nullable=False),
    sa.Column('bo_mobile_skin', sa.String(length=255), nullable=False),
    sa.Column('bo_include_head', sa.String(length=255), nullable=False),
    sa.Column('bo_include_tail', sa.String(length=255), nullable=False),
    sa.Column('bo_content_head', sa.Text(), nullable=False),
    sa.Column('bo_mobile_content_head', sa.Text(), nullable=False),
    sa.Column('bo_content_tail', sa.Text(), nullable=False),
    sa.Column('bo_mobile_content_tail', sa.Text(), nullable=False),
    sa.Column('bo_insert_content', sa.Text(), nullable=False),
    sa.Column('bo_gallery_cols', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_gallery_width', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_gallery_height', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_mobile_gallery_width', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_mobile_gallery_height', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_upload_size', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_reply_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_search', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_count_write', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_count_comment', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_write_min', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_write_max', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_comment_min', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_comment_max', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_notice', sa.Text(), nullable=False),
    sa.Column('bo_upload_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_email', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_cert', sa.Enum('', 'cert', 'adult', 'hp-cert', 'hp-adult'), nullable=False),
    sa.Column('bo_use_sns', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_use_captcha', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('bo_sort_field', sa.String(length=255), nullable=False),
    sa.Column('bo_1_subj', sa.String(length=255), nullable=False),
    sa.Column('bo_2_subj', sa.String(length=255), nullable=False),
    sa.Column('bo_3_subj', sa.String(length=255), nullable=False),
    sa.Column('bo_4_subj', sa.String(length=255), nullable=False),
    sa.Column('bo_5_subj', sa.String(length=255), nullable=False),
    sa.Column('bo_6_subj', sa.String(length=255), nullable=False),
    sa.Column('bo_7_subj', sa.String(length=255), nullable=False),
    sa.Column('bo_8_subj', sa.String(length=255), nullable=False),
    sa.Column('bo_9_subj', sa.String(length=255), nullable=False),
    sa.Column('bo_10_subj', sa.String(length=255), nullable=False),
    sa.Column('bo_1', sa.String(length=255), nullable=False),
    sa.Column('bo_2', sa.String(length=255), nullable=False),
    sa.Column('bo_3', sa.String(length=255), nullable=False),
    sa.Column('bo_4', sa.String(length=255), nullable=False),
    sa.Column('bo_5', sa.String(length=255), nullable=False),
    sa.Column('bo_6', sa.String(length=255), nullable=False),
    sa.Column('bo_7', sa.String(length=255), nullable=False),
    sa.Column('bo_8', sa.String(length=255), nullable=False),
    sa.Column('bo_9', sa.String(length=255), nullable=False),
    sa.Column('bo_10', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('bo_table')
    )
    op.create_table('g6_config',
    sa.Column('cf_id', sa.Integer(), nullable=False),
    sa.Column('cf_title', sa.String(length=255), nullable=False),
    sa.Column('cf_theme', sa.String(length=100), nullable=False),
    sa.Column('cf_admin', sa.String(length=100), nullable=False),
    sa.Column('cf_admin_email', sa.String(length=100), nullable=False),
    sa.Column('cf_admin_email_name', sa.String(length=100), nullable=False),
    sa.Column('cf_add_script', sa.Text(), nullable=False),
    sa.Column('cf_use_point', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_point_term', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_use_copy_log', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_use_email_certify', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_login_point', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_cut_name', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_nick_modify', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_new_skin', sa.String(length=50), nullable=False),
    sa.Column('cf_new_rows', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_search_skin', sa.String(length=50), nullable=False),
    sa.Column('cf_connect_skin', sa.String(length=50), nullable=False),
    sa.Column('cf_faq_skin', sa.String(length=50), nullable=False),
    sa.Column('cf_read_point', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_write_point', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_comment_point', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_download_point', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_write_pages', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_mobile_pages', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_link_target', sa.String(length=50), nullable=False),
    sa.Column('cf_bbs_rewrite', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_delay_sec', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_filter', sa.Text(), nullable=False),
    sa.Column('cf_possible_ip', sa.Text(), nullable=False),
    sa.Column('cf_intercept_ip', sa.Text(), nullable=False),
    sa.Column('cf_analytics', sa.Text(), nullable=False),
    sa.Column('cf_add_meta', sa.Text(), nullable=False),
    sa.Column('cf_syndi_token', sa.String(length=255), nullable=False),
    sa.Column('cf_syndi_except', sa.Text(), nullable=False),
    sa.Column('cf_member_skin', sa.String(length=50), nullable=False),
    sa.Column('cf_use_homepage', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_req_homepage', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_use_tel', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_req_tel', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_use_hp', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_req_hp', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_use_addr', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_req_addr', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_use_signature', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_req_signature', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_use_profile', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_req_profile', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_register_level', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_register_point', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_icon_level', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_use_recommend', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_recommend_point', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_leave_day', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_search_part', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_email_use', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_email_wr_super_admin', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_email_wr_group_admin', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_email_wr_board_admin', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_email_wr_write', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_email_wr_comment_all', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_email_mb_super_admin', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_email_mb_member', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_email_po_super_admin', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_prohibit_id', sa.Text(), nullable=False),
    sa.Column('cf_prohibit_email', sa.Text(), nullable=False),
    sa.Column('cf_new_del', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_memo_del', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_visit_del', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_popular_del', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_optimize_date', sa.String(length=10), nullable=False),
    sa.Column('cf_use_member_icon', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_member_icon_size', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_member_icon_width', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_member_icon_height', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_member_img_size', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_member_img_width', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_member_img_height', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_login_minutes', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_image_extension', sa.String(length=255), nullable=False),
    sa.Column('cf_flash_extension', sa.String(length=255), nullable=False),
    sa.Column('cf_movie_extension', sa.String(length=255), nullable=False),
    sa.Column('cf_formmail_is_member', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_page_rows', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_mobile_page_rows', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_visit', sa.String(length=255), nullable=False),
    sa.Column('cf_max_po_id', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_stipulation', sa.Text(), nullable=False),
    sa.Column('cf_privacy', sa.Text(), nullable=False),
    sa.Column('cf_open_modify', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_memo_send_point', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_mobile_new_skin', sa.String(length=50), nullable=False),
    sa.Column('cf_mobile_search_skin', sa.String(length=50), nullable=False),
    sa.Column('cf_mobile_connect_skin', sa.String(length=50), nullable=False),
    sa.Column('cf_mobile_faq_skin', sa.String(length=50), nullable=False),
    sa.Column('cf_mobile_member_skin', sa.String(length=50), nullable=False),
    sa.Column('cf_captcha_mp3', sa.String(length=255), nullable=False),
    sa.Column('cf_editor', sa.String(length=50), nullable=False),
    sa.Column('cf_cert_use', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_cert_find', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_cert_ipin', sa.String(length=255), nullable=False),
    sa.Column('cf_cert_hp', sa.String(length=255), nullable=False),
    sa.Column('cf_cert_simple', sa.String(length=255), nullable=False),
    sa.Column('cf_cert_kg_cd', sa.String(length=255), nullable=False),
    sa.Column('cf_cert_kg_mid', sa.String(length=255), nullable=False),
    sa.Column('cf_cert_kcb_cd', sa.String(length=255), nullable=False),
    sa.Column('cf_cert_kcp_cd', sa.String(length=255), nullable=False),
    sa.Column('cf_lg_mid', sa.String(length=100), nullable=False),
    sa.Column('cf_lg_mert_key', sa.String(length=100), nullable=False),
    sa.Column('cf_cert_limit', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_cert_req', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_sms_use', sa.String(length=255), nullable=False),
    sa.Column('cf_sms_type', sa.String(length=10), nullable=False),
    sa.Column('cf_icode_id', sa.String(length=255), nullable=False),
    sa.Column('cf_icode_pw', sa.String(length=255), nullable=False),
    sa.Column('cf_icode_server_ip', sa.String(length=50), nullable=False),
    sa.Column('cf_icode_server_port', sa.String(length=50), nullable=False),
    sa.Column('cf_icode_token_key', sa.String(length=100), nullable=False),
    sa.Column('cf_googl_shorturl_apikey', sa.String(length=50), nullable=False),
    sa.Column('cf_social_login_use', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cf_social_servicelist', sa.String(length=255), nullable=False),
    sa.Column('cf_payco_clientid', sa.String(length=100), nullable=False),
    sa.Column('cf_payco_secret', sa.String(length=100), nullable=False),
    sa.Column('cf_facebook_appid', sa.String(length=100), nullable=False),
    sa.Column('cf_facebook_secret', sa.String(length=100), nullable=False),
    sa.Column('cf_twitter_key', sa.String(length=100), nullable=False),
    sa.Column('cf_twitter_secret', sa.String(length=100), nullable=False),
    sa.Column('cf_google_clientid', sa.String(length=100), nullable=False),
    sa.Column('cf_google_secret', sa.String(length=100), nullable=False),
    sa.Column('cf_naver_clientid', sa.String(length=100), nullable=False),
    sa.Column('cf_naver_secret', sa.String(length=100), nullable=False),
    sa.Column('cf_kakao_rest_key', sa.String(length=100), nullable=False),
    sa.Column('cf_kakao_client_secret', sa.String(length=100), nullable=False),
    sa.Column('cf_kakao_js_apikey', sa.String(length=100), nullable=False),
    sa.Column('cf_captcha', sa.String(length=100), nullable=False),
    sa.Column('cf_recaptcha_site_key', sa.String(length=100), nullable=False),
    sa.Column('cf_recaptcha_secret_key', sa.String(length=100), nullable=False),
    sa.Column('cf_1_subj', sa.String(length=255), nullable=False),
    sa.Column('cf_2_subj', sa.String(length=255), nullable=False),
    sa.Column('cf_3_subj', sa.String(length=255), nullable=False),
    sa.Column('cf_4_subj', sa.String(length=255), nullable=False),
    sa.Column('cf_5_subj', sa.String(length=255), nullable=False),
    sa.Column('cf_6_subj', sa.String(length=255), nullable=False),
    sa.Column('cf_7_subj', sa.String(length=255), nullable=False),
    sa.Column('cf_8_subj', sa.String(length=255), nullable=False),
    sa.Column('cf_9_subj', sa.String(length=255), nullable=False),
    sa.Column('cf_10_subj', sa.String(length=255), nullable=False),
    sa.Column('cf_1', sa.String(length=255), nullable=False),
    sa.Column('cf_2', sa.String(length=255), nullable=False),
    sa.Column('cf_3', sa.String(length=255), nullable=False),
    sa.Column('cf_4', sa.String(length=255), nullable=False),
    sa.Column('cf_5', sa.String(length=255), nullable=False),
    sa.Column('cf_6', sa.String(length=255), nullable=False),
    sa.Column('cf_7', sa.String(length=255), nullable=False),
    sa.Column('cf_8', sa.String(length=255), nullable=False),
    sa.Column('cf_9', sa.String(length=255), nullable=False),
    sa.Column('cf_10', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('cf_id')
    )
    op.create_table('g6_group',
    sa.Column('gr_id', sa.String(length=10), nullable=False),
    sa.Column('gr_subject', sa.String(length=255), nullable=False),
    sa.Column('gr_device', sa.Enum('both', 'pc', 'mobile'), nullable=False),
    sa.Column('gr_admin', sa.String(length=255), nullable=False),
    sa.Column('gr_use_access', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('gr_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('gr_1_subj', sa.String(length=255), nullable=False),
    sa.Column('gr_2_subj', sa.String(length=255), nullable=False),
    sa.Column('gr_3_subj', sa.String(length=255), nullable=False),
    sa.Column('gr_4_subj', sa.String(length=255), nullable=False),
    sa.Column('gr_5_subj', sa.String(length=255), nullable=False),
    sa.Column('gr_6_subj', sa.String(length=255), nullable=False),
    sa.Column('gr_7_subj', sa.String(length=255), nullable=False),
    sa.Column('gr_8_subj', sa.String(length=255), nullable=False),
    sa.Column('gr_9_subj', sa.String(length=255), nullable=False),
    sa.Column('gr_10_subj', sa.String(length=255), nullable=False),
    sa.Column('gr_1', sa.String(length=255), nullable=False),
    sa.Column('gr_2', sa.String(length=255), nullable=False),
    sa.Column('gr_3', sa.String(length=255), nullable=False),
    sa.Column('gr_4', sa.String(length=255), nullable=False),
    sa.Column('gr_5', sa.String(length=255), nullable=False),
    sa.Column('gr_6', sa.String(length=255), nullable=False),
    sa.Column('gr_7', sa.String(length=255), nullable=False),
    sa.Column('gr_8', sa.String(length=255), nullable=False),
    sa.Column('gr_9', sa.String(length=255), nullable=False),
    sa.Column('gr_10', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('gr_id')
    )
    op.create_table('g6_member',
    sa.Column('mb_no', sa.Integer(), nullable=False),
    sa.Column('mb_id', sa.String(length=20), nullable=False),
    sa.Column('mb_password', sa.String(length=255), nullable=False),
    sa.Column('mb_name', sa.String(length=255), nullable=False),
    sa.Column('mb_nick', sa.String(length=255), nullable=False),
    sa.Column('mb_nick_date', sa.String(length=30), nullable=False),
    sa.Column('mb_email', sa.String(length=255), nullable=False),
    sa.Column('mb_homepage', sa.String(length=255), nullable=False),
    sa.Column('mb_level', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('mb_sex', sa.String(length=1), nullable=False),
    sa.Column('mb_birth', sa.String(length=255), nullable=False),
    sa.Column('mb_tel', sa.String(length=255), nullable=False),
    sa.Column('mb_hp', sa.String(length=255), nullable=False),
    sa.Column('mb_certify', sa.String(length=20), nullable=False),
    sa.Column('mb_adult', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('mb_dupinfo', sa.String(length=255), nullable=False),
    sa.Column('mb_zip1', sa.String(length=3), nullable=False),
    sa.Column('mb_zip2', sa.String(length=3), nullable=False),
    sa.Column('mb_addr1', sa.String(length=255), nullable=False),
    sa.Column('mb_addr2', sa.String(length=255), nullable=False),
    sa.Column('mb_addr3', sa.String(length=255), nullable=False),
    sa.Column('mb_addr_jibeon', sa.String(length=255), nullable=False),
    sa.Column('mb_signature', sa.Text(), nullable=False),
    sa.Column('mb_recommend', sa.String(length=255), nullable=False),
    sa.Column('mb_point', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('mb_today_login', sa.String(length=19), nullable=False),
    sa.Column('mb_login_ip', sa.String(length=255), nullable=False),
    sa.Column('mb_datetime', sa.String(length=30), nullable=False),
    sa.Column('mb_ip', sa.String(length=255), nullable=False),
    sa.Column('mb_leave_date', sa.String(length=8), nullable=False),
    sa.Column('mb_intercept_date', sa.String(length=8), nullable=False),
    sa.Column('mb_email_certify', sa.String(length=30), nullable=False),
    sa.Column('mb_email_certify2', sa.String(length=255), nullable=False),
    sa.Column('mb_memo', sa.Text(), nullable=False),
    sa.Column('mb_lost_certify', sa.String(length=255), nullable=False),
    sa.Column('mb_mailling', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('mb_sms', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('mb_open', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('mb_open_date', sa.String(length=30), nullable=False),
    sa.Column('mb_profile', sa.Text(), nullable=False),
    sa.Column('mb_memo_call', sa.String(length=255), nullable=False),
    sa.Column('mb_memo_cnt', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('mb_scrap_cnt', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('mb_1', sa.String(length=255), nullable=False),
    sa.Column('mb_2', sa.String(length=255), nullable=False),
    sa.Column('mb_3', sa.String(length=255), nullable=False),
    sa.Column('mb_4', sa.String(length=255), nullable=False),
    sa.Column('mb_5', sa.String(length=255), nullable=False),
    sa.Column('mb_6', sa.String(length=255), nullable=False),
    sa.Column('mb_7', sa.String(length=255), nullable=False),
    sa.Column('mb_8', sa.String(length=255), nullable=False),
    sa.Column('mb_9', sa.String(length=255), nullable=False),
    sa.Column('mb_10', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('mb_no'),
    sa.UniqueConstraint('mb_email'),
    sa.UniqueConstraint('mb_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('g6_member')
    op.drop_table('g6_group')
    op.drop_table('g6_config')
    op.drop_table('g6_board')
    # ### end Alembic commands ###