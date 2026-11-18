"""Source-only candidate for the original PREPARED L0 PUSH call site.

The already prepared resolver owns the private approach and the immutable
push/placement goal. Do not put movement XY keys in a selected PUSH option.
This adapter is not an admission decision or a physical execution authority.
"""
def make_selected_push_option(*, target_ref, distance_m, surface_height_m,
                              attempt_id, original_goal_sha256, entry_receipt):
    from ainav.native.behavior_authority import BehaviorOption
    return BehaviorOption('original-L0-PUSH','PUSH',target_ref,
        (('push_distance_m',distance_m),('surface_height_m',surface_height_m)),
        60.,entry_receipt,attempt_id=attempt_id,original_push_goal_sha256=original_goal_sha256)
